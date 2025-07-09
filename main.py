import asyncio
import csv
import sys
from playwright.async_api import async_playwright
from urllib.parse import urljoin



SEARCH_IFRAME_URL = "https://members.tahoemls.com/public/members_search.cfm"
MAIN_PAGE_URL = "https://tahoemls.com/general/?https://members.tahoemls.com/public/members_search.cfm"
BASE_URL = "https://members.tahoemls.com/public/"
CONCURRENCY_LEVEL = 10  # Number of profiles to scrape at the same time


async def scrape_profile_page(context, url):
    """
    Scrapes detailed information from a single profile page with retry logic.
    This version handles both pages with and without an iframe.
    """
    for attempt in range(3):
        page = await context.new_page()
        try:
            # Increased timeout to 90 seconds
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)

            frame = page.frame(name="main")
            scrape_context = frame if frame else page

            if frame:
                await frame.wait_for_load_state("domcontentloaded", timeout=15000)

            async def get_text_by_label(label):
                xpath = f"//td[b[contains(text(), '{label}')]]/following-sibling::td[1]"
                locator = scrape_context.locator(xpath)
                if await locator.count() > 0:
                    text = await locator.first.text_content()
                    return text.strip() if text else ""
                return ""

            data = {}
            data["Name"] = await get_text_by_label("Name:")
            if not data["Name"]:
                print(f"Could not find 'Name' for profile on page {url}")
            data["Office"] = await get_text_by_label("Office:")
            data["Address"] = await get_text_by_label("Address:")
            data["Office ph"] = await get_text_by_label("Office Ph:")
            data["Cell Ph"] = await get_text_by_label("Cell Ph:")

            email_locator = scrape_context.locator("//td[b[contains(text(), 'E-mail:')]]/following-sibling::td[1]//a")
            if await email_locator.count() > 0:
                href = await email_locator.first.get_attribute("href")
                data["E-mail"] = href.replace("mailto:", "").strip() if href else ""
            else:
                data["E-mail"] = await get_text_by_label("E-mail:")

            website_locator = scrape_context.locator("//td[b[contains(text(), 'Website:')]]/following-sibling::td[1]//a")
            if await website_locator.count() > 0:
                data["Website"] = await website_locator.first.get_attribute("href") or ""
            else:
                data["Website"] = await get_text_by_label("Website:")

            return data # Success, exit the retry loop

        except Exception as e:
            print(f"❌ Attempt {attempt + 1}/3 failed for {url}: {e}")
            if page and not page.is_closed(): # Close page on failure before retry
                await page.close()
            if attempt < 2:
                await asyncio.sleep(5) # Wait 5 seconds before retrying
            else:
                print(f"❌ All 3 attempts failed for {url}. Skipping.")
                return None # All retries failed
        finally:
            if page and not page.is_closed(): # Ensure page exists and is not closed
                await page.close()
    return None # Should not be reached, but as a fallback


async def get_profile_links_from_search(frame):
    """Collects all profile links from the search result pages."""
    profile_links = set()
    page_num = 1
    while True:
        try:
            await frame.wait_for_selector('tr.trResultsRowAlt, tr.trResultsRow', timeout=15000)
        except Exception:
            # This means we've reached the last page of results
            break
            
        rows = await frame.locator('tr.trResultsRow, tr.trResultsRowAlt').all()

        for row in rows:
            name_link = row.locator('td:first-child a').first
            if await name_link.count() > 0:
                href = await name_link.get_attribute("href") or ""
                if "offices_profile.cfm" not in href and href:
                    full_url = urljoin(BASE_URL, href)
                    profile_links.add(full_url)

        next_button = frame.locator('xpath=//a[normalize-space(text())="Next"]').first
        if await next_button.count() > 0:
            await next_button.click()
            await frame.wait_for_load_state('domcontentloaded', timeout=15000)
            await asyncio.sleep(1) # A small delay to ensure the page updates
            page_num += 1
        else:
            break
    return list(profile_links)


async def run():
    async with async_playwright() as p:
        # Using headless=True for production/clean runs
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        all_results = []
        profile_links = []

        print("🔎 Performing a search for all members...")
        try:
            await page.goto(MAIN_PAGE_URL, wait_until="domcontentloaded", timeout=30000)

            iframe_element = await page.wait_for_selector('iframe#idxc_iframe', timeout=15000)
            await iframe_element.evaluate(f'el => el.src = "{SEARCH_IFRAME_URL}"')
            
            frame = await iframe_element.content_frame()
            if not frame:
                raise Exception("Could not find iframe content.")

            await frame.wait_for_selector('input[name="LastName"]', timeout=15000, state="visible")
            await frame.locator('input[type="submit"], button[type="submit"]').click()

            profile_links = await get_profile_links_from_search(frame)
            print(f"🔗 Found {len(profile_links)} total profiles to scrape.")

        except Exception as e:
            print(f"❌ An error occurred during the search phase: {e}")
        finally:
            await page.close() # Close the initial search page

        if profile_links:
            total_links = len(profile_links)
            print(f"🚀 Starting to scrape {total_links} profiles with {CONCURRENCY_LEVEL} parallel tasks...")
            
            semaphore = asyncio.Semaphore(CONCURRENCY_LEVEL)
            scrape_count = 0
            lock = asyncio.Lock()
            
            async def scrape_with_semaphore(link):
                nonlocal scrape_count
                async with semaphore: # Acquire the semaphore
                    # Scrape the page
                    result = await scrape_profile_page(context, link)
                    # Safely increment and print the counter
                    async with lock:
                        scrape_count += 1
                        # Use carriage return to show progress on a single line
                        # Clear the line and then write the progress
                        sys.stdout.write("\r" + " " * 50 + "\r") # Clear line with spaces
                        sys.stdout.write(f"  Progress: [{scrape_count}/{total_links}]")
                        sys.stdout.flush()
                    return result

            tasks = [scrape_with_semaphore(link) for link in profile_links]
            
            results = await asyncio.gather(*tasks)
            print() # Newline after the progress bar is done
            
            # Filter out None results from failed scrapes and empty dicts
            all_results = [res for res in results if res and any(res.values())]

        print(f"\n🎯 Total profiles successfully scraped: {len(all_results)}")
        
        if all_results:
            fieldnames = ["Name", "Office", "Address", "Office ph", "Cell Ph", "E-mail", "Website"]
            with open("results.csv", mode="w", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_results)
            print("✅ Results saved to results.csv")
        else:
            print("🤷 No results to save.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
