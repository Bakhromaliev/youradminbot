from ntscraper import Nitter
import logging

logging.basicConfig(level=logging.INFO)
scraper = Nitter()
try:
    print("Testing @theMadridZone on xcancel.com...")
    data = scraper.get_tweets("theMadridZone", mode='user', number=3, instance="https://xcancel.com")
    print(f"Data: {data}")
except Exception as e:
    print(f"Error: {e}")
