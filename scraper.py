import requests
from bs4 import BeautifulSoup
import re
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import time

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "car_listings"

print("Connecting to Supabase...")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

START_PAGE = 1
END_PAGE = 20

print(f"Starting optimized extraction from page {START_PAGE} to {END_PAGE}...\n")

for page in range(START_PAGE, END_PAGE + 1):
    URL = f"https://www.autoscout24.ro/lst/bmw/seria-3-toate?page={page}"
    print(f"--- Scraping Page {page} ---")
    print("Sending request to AutoScout24...")
    response = requests.get(URL, headers=headers)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print(f"Access granted for page {page}. Starting extraction...\n")
        soup = BeautifulSoup(response.text, 'html.parser')
    
        all_url_paths = set(re.findall(r'(/(?:oferte|offers)/[^"\'\s>]+)', response.text))
        cars = soup.find_all("article", attrs={"data-testid": "list-item"})
        print(f"Found {len(cars)} cars on this page.\n")

        current_page_ids = [car.get("data-guid") for car in cars if car.get("data-guid")]
        existing_records = {}
        if current_page_ids:
            try:
                db_response = supabase.table(TABLE_NAME).select("car_id, price").in_("car_id", current_page_ids).execute()
                for row in db_response.data:
                    existing_records[row["car_id"]] = row["price"]
            except Exception as e:
                print(f"Warning: Could not fetch validation batch from DB: {e}")

        scraped_cars_batch = []
        new_or_changed_count = 0
        for car in cars:
            car_id = car.get("data-guid")
            if not car_id:
                continue
            make = car.get("data-make")
            raw_price = car.get("data-price")
            raw_model_year = car.get("data-first-registration")
            raw_mileage = car.get("data-mileage")
            model = car.get("data-model")
            fuel_letter = car.get("data-fuel-type")
            fuel_map = {"b": "Gasoline", "d": "Diesel", "e": "Electric", "2": "Hybrid"}
            fuel_type = fuel_map.get(fuel_letter, "Unknown")
            full_link = "Without link"
            card_text = car.get_text(separator=" ", strip=True)
            hp_match = re.search(r'(\d+)\s*CP', card_text)
            raw_power_hp = hp_match.group(1) if hp_match else None       
            trans_match = re.search(r'(Automat[a-zăâ]*|Manual[a-zăâ]*)', card_text, re.IGNORECASE)
            transmission = trans_match.group(1).capitalize() if trans_match else "Unknown"

            clean_price = float(raw_price) if raw_price else None
            clean_model_year = int(raw_model_year.split("-")[-1]) if raw_model_year else None
            clean_power_hp = int(raw_power_hp) if raw_power_hp else None
            clean_mileage = int(raw_mileage) if raw_mileage else None

            # --- FILTERING LOGIC ---
            if car_id in existing_records:
                old_price = existing_records[car_id]
                if old_price == clean_price:
                    # It's an exact duplicate, skip it silently to keep terminal clean
                    continue
                else:
                    print(f"Price difference detected! {car_id[:8]}... Old: {old_price} -> New: {clean_price}")
            else:
                pass # Brand new car, we will add it
            
            for path in all_url_paths:
                if car_id in path:
                    full_link = f"https://www.autoscout24.ro{path}"
                    break

            car_data = {
                "car_id": car_id,
                "make": str(make).capitalize(),
                "model": model,
                "price": clean_price,
                "mileage": clean_mileage,
                "model_year": clean_model_year,
                "power_hp": clean_power_hp,
                "fuel_type": fuel_type,
                "transmission": transmission,
                "listing_link": full_link
            }
            
            scraped_cars_batch.append(car_data)
            new_or_changed_count += 1
        print(f"Successfully processed {len(scraped_cars_batch)} cars.")
    
    # --- DATABASE INSERTION ---
        print(f"Inserting data into Supabase table '{TABLE_NAME}'...")
        if scraped_cars_batch:
            try:
                data, count = supabase.table(TABLE_NAME).insert(scraped_cars_batch).execute()
                print(f"✅ Inserted {new_or_changed_count}/{len(scraped_cars_batch)} new/updated cars from page {page}.")
            except Exception as e:
                print(f"Database error on page {page}: {e}")
        else:
            print(f"⏭️  No new data on page {page}. All cars already up to date.")

        time.sleep(2)
    elif response.status_code == 403:
        print("Error 403: Site detected a bot and blocked us.")
    else:
        print(f"Received unexpected status code: {response.status_code}")

print("\nScraping complete!")