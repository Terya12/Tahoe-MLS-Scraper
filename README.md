# Tahoe MLS Scraper

This project is a web scraper designed to extract member information from the Tahoe MLS website. It utilizes Playwright to automate browser interactions and gather data, which is then saved to a CSV file.

## Features

- Scrapes member profiles from the Tahoe MLS website.
- Handles pagination to collect all member links.
- Asynchronously scrapes multiple profiles for efficiency.
- Saves the collected data (Name, Office, Address, Phone, Email, Website) into a `results.csv` file.

## Setup and Installation

To get the scraper up and running, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Terya12/Tahoe-MLS-Scraper
    cd tahoemls_scraper
    ```

2.  **Create and activate a virtual environment:**
    It is recommended to use a virtual environment to manage project dependencies.

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the required dependencies:**
    The necessary Python packages are listed in the `requirements.txt` file.

    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers:**
    Playwright requires browser binaries to be installed.

    ```bash
    playwright install
    ```

## Usage

Once the setup is complete, you can run the scraper with the following command:

```bash
python3 main.py
```

The script will start scraping the website, and you will see progress updates in the console. Upon completion, the scraped data will be saved in the `results.csv` file in the project's root directory.

## Project Structure

- `main.py`: The main script containing the scraping logic.
- `requirements.txt`: A list of Python dependencies for the project.
- `results.csv`: The output file where the scraped data is stored.
- `README.md`: This file, providing an overview and instructions for the project.
