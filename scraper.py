import re
import json
import base64
import pandas as pd
import random
import logging
import traceback

from collections import defaultdict
from curl_cffi import requests

from settings import PROFILES_TO_PROXIES, RETRY_ATTEMPTS
from adspower_client import AdsPowerManager

# Set up logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class StubhubScraper:
    """
    A scraper class to fetch event URLs and ticket listings from StubHub using rotating
     proxies and session management.
    """

    def __init__(self):
        """
        Initialize the StubhubScraper with the given profile ID.

        Args:
            profile_id (str): Profile ID to fetch proxy, rotation details and
             a reference to ads power profile.
        """
        self.cookies = None
        self.user_agent = None
        self.profile_id = None
        self.proxy = None
        self.rotation_link = None

    def update_with_random_profile(self):
        """
        Select a random profile from available profiles and update the proxy details.
        """
        profile_id = random.choice(list(PROFILES_TO_PROXIES.keys()))
        self.profile_id = profile_id
        self.proxy = PROFILES_TO_PROXIES[profile_id]['proxy']
        self.rotation_link = PROFILES_TO_PROXIES[profile_id].get('rotation_url')

    def rotate_proxy(self):
        """Rotates the proxy"""
        import requests

        if self.rotation_link:
            response = requests.get(self.rotation_link)
            return response.status_code == 200

    def update_cookies(self):
        """
        Fetch new cookies and user-agent for the current profile using AdsPowerManager.
        """
        self.rotate_proxy()
        ads_power_client = AdsPowerManager()
        self.cookies, self.user_agent = ads_power_client.get_cookies(self.profile_id )

    @staticmethod
    def encode_lat_lon_stubhub(coordinates):
        """
        Encode latitude or longitude as a StubHub-compatible base64 string.

        Args:
            coordinates (float): Latitude or longitude value.

        Returns:
            str: Encoded value as a base64 string.
        """
        value_str = f"{coordinates:.8f}"
        encoded_bytes = base64.b64encode(value_str.encode('utf-8'))
        decoded_location = encoded_bytes.decode('utf-8')
        decoded_location = decoded_location.replace('=', '%3D')
        return decoded_location

    @staticmethod
    def save_events_urls(events_urls):
        """
        Save event URLs to a CSV file.

        Args:
            events_urls (list): List of event URL dictionaries.
        """
        df = pd.DataFrame(events_urls)
        df.to_csv("events_urls.csv", encoding="utf-8", index=False)

    def get_event_urls(self, lat_lng_state_list, retry_attempts=3):
        """
        Fetch event URLs from StubHub for the given locations.

        Args:
            lat_lng_state_list (list): List of location dictionaries with latitude, longitude, and state.
            retry_attempts (int): Number of retry attempts for failed requests.

        Returns:
            list: List of event URL dictionaries.
        """
        event_urls = []  # Initialize the list to store event URLs

        logging.info("Starting to fetch event URLs for given locations.")

        for lat_lng_state in lat_lng_state_list:
            temp_list = []  # Temporary list to track URLs for the current location
            encoded_lat = self.encode_lat_lon_stubhub(lat_lng_state["latitude"])
            encoded_lon = self.encode_lat_lon_stubhub(lat_lng_state["longitude"])

            # Construct the base URL with encoded latitude and longitude
            base_url = "https://www.stubhub.com/explore?method=getExploreEvents"
            url_with_coordinates = f"{base_url}&lat={encoded_lat}&lon={encoded_lon}"
            page_count = 0

            logging.debug(f"Processing location: {lat_lng_state}")

            while True:
                payload = {}  # Empty payload for GET request
                headers = {
                    'accept': '*/*',
                    'accept-language': 'en-US,en;q=0.9',
                    'content-type': 'application/json',
                    'cookies': self.cookies,
                    'user-agent': self.user_agent
                }

                # Append the current page number to the URL for pagination
                url_with_pagination = url_with_coordinates + f"&page={page_count}"

                # Retry mechanism for handling failed requests
                for attempt in range(1, retry_attempts + 1):
                    try:
                        proxies = {
                            "http": self.proxy,
                            "https": self.proxy
                        }
                        response = requests.get(
                            url_with_pagination,
                            headers=headers,
                            proxies=proxies,
                            data=payload
                        )
                        logging.info(
                            f"Requesting URL: {url_with_pagination}, Status Code: {response.status_code}, Page Count: {page_count}")

                        if response.status_code != 200:  # Check if response status is not OK
                            if attempt < retry_attempts:
                                logging.warning(
                                    f"Request failed with status code {response.status_code}. Retrying attempt {attempt}...")
                                self.update_cookies()  # Refresh cookies before retrying
                                headers["cookies"] = self.cookies
                                headers['user-agent'] = self.user_agent
                            else:
                                logging.error(
                                    f"Max retry attempts reached. Request failed for URL: {url_with_pagination}")
                                exit()  # Exit the loop if max retry attempts are reached
                        break  # Exit the retry loop if request is successful
                    except Exception as e:
                        logging.error(f"Attempt {attempt} failed: {e}")
                        logging.debug(traceback.format_exc())  # Log the stack trace for debugging
                        if attempt < retry_attempts:
                            logging.warning("Retrying after refreshing cookies...")
                            self.update_cookies()
                            headers["cookies"] = self.cookies
                            headers['user-agent'] = self.user_agent
                        else:
                            logging.critical("Max retry attempts reached. Exiting.")
                            exit()

                events_data = response.json()  # Parse the response JSON
                if events_data.get("events"):  # Check if there are events in the response
                    for event in events_data["events"]:
                        if event["url"] not in temp_list:  # Avoid duplicate URLs
                            temp_list.append(event["url"])
                            event_dict = {
                                "Url": event["url"],
                                "State": lat_lng_state["state"]
                            }
                            event_urls.append(event_dict)

                            # Stop if we have collected 100 events
                            if len(event_urls) == 100:
                                logging.info("Reached 100 events limit. Stopping further requests.")
                                break

                # Save the event URLs to a JSON file after each page request
                with open("event_urls.json", "w", encoding="utf-8") as f:
                    json.dump(event_urls, f, ensure_ascii=False, indent=4)
                    logging.debug("Event URLs saved to event_urls.json")

                # Stop fetching if 100 events are collected or no remaining events
                if len(event_urls) == 100:
                    break
                if events_data["remaining"] == 0:
                    logging.info(f"No remaining events for location: {lat_lng_state}")
                    break

                page_count += 1  # Increment page count for pagination

        logging.info("Completed fetching event URLs.")
        return event_urls

    def get_event_listings(self, event_urls, retry_attempts):
        """
        Fetch event listings from StubHub for the given event URLs.

        Args:
            event_urls (list): List of event URL dictionaries with state information.
            retry_attempts (int): Number of retry attempts for failed requests.

        Returns:
            defaultdict: Dictionary containing ticket details grouped by state.
        """
        tickets_details_dict = defaultdict(list)  # Initialize a dictionary to store ticket details

        logging.info("Starting to fetch event listings for the provided URLs.")

        for event_obj in event_urls:
            event_listing = []  # Initialize a list to store ticket listings for the current event
            event_url = event_obj["Url"]
            state = event_obj["State"]
            page_count = 1

            logging.debug(f"Processing event URL: {event_url} for state: {state}")

            while True:
                headers = {
                    'accept': '*/*',
                    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
                    'cache-control': 'no-cache',
                    'content-type': 'application/json',
                    'cookie': self.cookies,
                    'origin': 'https://www.stubhub.com',
                    'pragma': 'no-cache',
                    'priority': 'u=1, i',
                    'referer': f'{event_url}/?quantity=2',
                    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': f'{self.user_agent}',
                }

                json_data = {
                    'ShowAllTickets': True,
                    'HideDuplicateTicketsV2': False,
                    'Quantity': 2,
                    'IsInitialQuantityChange': False,
                    'PageVisitId': '8B9A160A-F8B7-4256-9412-827CB48FD137',
                    'PageSize': 20,
                    'CurrentPage': page_count,
                    'SortBy': 'NEWPRICE',
                    'SortDirection': 0,
                    'Sections': '',
                    'Rows': '',
                    'Seats': '',
                    'SeatTypes': '',
                    'TicketClasses': '',
                    'ListingNotes': '',
                    'PriceRange': '0,100',
                    'InstantDelivery': False,
                    'EstimatedFees': False,
                    'BetterValueTickets': True,
                    'PriceOption': '',
                    'HasFlexiblePricing': False,
                    'ExcludeSoldListings': False,
                    'RemoveObstructedView': False,
                    'NewListingsOnly': False,
                    'PriceDropListingsOnly': False,
                    'SelectBestListing': False,
                    'ConciergeTickets': False,
                    'Favorites': False,
                    'Method': 'IndexSh',
                }

                # Retry mechanism for handling failed requests
                for attempt in range(1, retry_attempts + 1):
                    try:
                        proxies = {
                            "http": self.proxy,
                            "https": self.proxy
                        }
                        response = requests.post(
                            event_url,
                            headers=headers,
                            proxies=proxies,
                            json=json_data
                        )
                        logging.info(
                            f"Requesting URL: {event_url}, Status Code: {response.status_code}, Page Count: {page_count}")

                        if response.status_code != 200:
                            if attempt < retry_attempts:
                                logging.warning(
                                    f"Request failed with status code {response.status_code}. Retrying attempt {attempt}...")
                                self.update_cookies()  # Refresh cookies before retrying
                                headers["cookies"] = self.cookies
                                headers['user-agent'] = self.user_agent
                            else:
                                logging.error("Max retry attempts reached. Request failed.")
                                exit()
                        break  # Exit the retry loop if request is successful
                    except Exception as e:
                        logging.error(f"Attempt {attempt} failed: {e}")
                        logging.debug(traceback.format_exc())  # Log stack trace for debugging
                        if attempt < retry_attempts:
                            logging.warning("Retrying after refreshing cookies...")
                            self.update_cookies()
                            headers["cookies"] = self.cookies
                            headers['user-agent'] = self.user_agent
                        else:
                            logging.critical("Max retry attempts reached. Exiting.")
                            exit()

                listing_details = response.json()  # Parse the response JSON

                if not listing_details["items"]:  # Break if no more items are found
                    logging.info(f"No more listings found for URL: {event_url}")
                    break

                for ticket in listing_details["items"]:
                    event_listing.append(ticket)

                logging.debug(f"Collected {len(listing_details['items'])} tickets for page {page_count}.")

                page_count += 1  # Increment the page count for the next page

            tickets_details_dict[state].append(event_listing)  # Group event listings by state

            # Save the ticket details to a JSON file after processing each event
            with open("ticket_details.json", "w", encoding="utf-8") as f:
                json.dump(tickets_details_dict, f, ensure_ascii=False, indent=4)
                logging.debug("Ticket details saved to ticket_details.json")

        logging.info("Completed fetching event listings.")
        return tickets_details_dict


if __name__ =="__main__":

    # Initialize scraper client
    scraper_client = StubhubScraper()

    # Update scraper client with a random profile and cookies
    logging.info("Initializing scraper client with a random profile and updating cookies.")
    scraper_client.update_with_random_profile()
    scraper_client.update_cookies()

    # Load geo-location data from JSON file
    logging.info("Loading geo-location data from us-cities.json.")
    with open("us-cities.json", "r", encoding="utf-8") as f:
        geo_locations = json.load(f)

    # Get event URLs using the provided geo-locations
    logging.info("Fetching event URLs based on geo-locations.")
    all_event_urls = scraper_client.get_event_urls(geo_locations, RETRY_ATTEMPTS)

    # Save the fetched event URLs to a file
    logging.info("Saving fetched event URLs to a file.")
    scraper_client.save_events_urls(all_event_urls)

    # Fetch event listings for the saved event URLs
    logging.info("Starting to fetch event listings for all saved URLs.")
    scraper_client.get_event_listings(all_event_urls, RETRY_ATTEMPTS)

    logging.info("Completed fetching all event listings.")
