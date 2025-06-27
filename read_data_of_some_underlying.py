import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import pytz
import csv
import os
import time
import holidays  # pip install holidays

# Time zone setup
melbourne_tz = pytz.timezone('Australia/Melbourne')
us_eastern_tz = pytz.timezone('US/Eastern')

# Directory for storing CSV files
output_dir = "data"
os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists

def get_current_file(company, market):
    """Generate file name based on the current date, company, and market."""
    today = datetime.now().strftime('%Y-%m-%d')  # Use daily filenames
    return os.path.join(output_dir, f"{company}_{market}_prices_{today}.csv")

def is_market_open():
    """
    Check if the US market is open based on Eastern Time, excluding weekends, holidays, and early closing days.
    Returns True if the market is open, otherwise False.
    """
    # Get current US Eastern Time
    melbourne_time = datetime.now(melbourne_tz)
    us_eastern_time = melbourne_time.astimezone(us_eastern_tz)
    current_date = us_eastern_time.date()

    # Define US market hours
    market_open = us_eastern_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = us_eastern_time.replace(hour=16, minute=0, second=0, microsecond=0)
    market_half_close = us_eastern_time.replace(hour=13, minute=0, second=0, microsecond=0)  # Half-day close

    # US holidays
    us_holidays = holidays.US(years=current_date.year, observed=True)

    # Special half-day trading dates (e.g., Christmas Eve, Thanksgiving Friday)
    half_day_trading_dates = {
        datetime(current_date.year, 12, 24).date(),  # Christmas Eve
        datetime(current_date.year, 11, 24).date(),  # Day after Thanksgiving (example for 2024)
    }

    # Check conditions
    is_weekday = us_eastern_time.weekday() < 5  # Monday-Friday are 0-4
    is_not_holiday = current_date not in us_holidays
    if current_date in half_day_trading_dates:
        is_within_hours = market_open <= us_eastern_time <= market_half_close
    else:
        is_within_hours = market_open <= us_eastern_time <= market_close

    # Return True if all conditions are met
    return is_weekday and is_not_holiday and is_within_hours

def get_price(company, market):
    """Fetch the stock price for the given company and market from Google Finance."""
    url = f'https://www.google.com/finance/quote/{company}:{market}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            price_element = soup.find('div', class_='YMlKec fxKbKc')
            if price_element:
                try:
                    return float(price_element.text.replace(',', '').replace('$', ''))
                except ValueError:
                    return None
    except Exception as e:
        print(f"Error fetching price for {company}:{market}: {e}")
    return None

def save_price_to_csv(price, company, market):
    """Save the price with a timestamp to a date-specific CSV file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    file_path = get_current_file(company, market)

    # Check if file exists; if not, write the header
    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "price"])  # Write header

    # Append data to the file
    with open(file_path, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, price])
    print(f"Saved: {timestamp}, {price}")

def main():
    """Fetch and save stock prices every 5 seconds during market hours."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Fetch and save stock prices for a given company and market.")
    parser.add_argument('--company', type=str, required=True, help="The stock symbol of the company (e.g., 'NVDA' for NVIDIA).")
    parser.add_argument('--market', type=str, required=True, help="The stock market code (e.g., 'NASDAQ', 'NYSE').")
    args = parser.parse_args()
    company = args.company.upper()  # Ensure company symbol is uppercase
    market = args.market.upper()  # Ensure market code is uppercase

    print(f"Starting price fetcher for {company} on {market}")

    while True:
        if is_market_open():
            price = get_price(company, market)
            if price is not None:
                save_price_to_csv(price, company, market)
            else:
                print(f"Failed to fetch price for {company} on {market}. Retrying in 5 seconds.")
        else:
            print("Market is closed. Skipping fetch.")
        time.sleep(5)  # Wait for 5 seconds before the next attempt

if __name__ == "__main__":
    main()
