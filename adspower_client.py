import time
import requests
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from settings import ADSPOWER_BASE_URL  # Import the base URL for AdsPower API from settings

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class AdsPowerManager:
    def __init__(self):
        # Initialize with the base URL for AdsPower API
        self.base_url = ADSPOWER_BASE_URL

    def get_ws_endpoint(self, profile_id):
        """
        Get the WebSocket endpoint and webdriver path for a given profile.

        Args:
            profile_id (str): The ID of the profile to fetch the endpoint for.

        Returns:
            tuple: WebSocket endpoint and webdriver path.
        """
        # Construct the URL for the API request to start the browser for the given profile
        url = f"{self.base_url}/api/v1/browser/start?user_id={profile_id}&ip_tab=0&open_tabs=1&clear_cache_after_closing=1&launch_args=[%22-no-sandbox%22]"
        response = requests.get(url=url)

        # Raise an exception for failed requests (non-2xx status codes)
        response.raise_for_status()

        # Parse the JSON response to extract the WebSocket endpoint and webdriver path
        data = response.json()
        ws_endpoint = data["data"]["ws"]["selenium"]
        webdriver_path = data["data"]["webdriver"]

        return ws_endpoint, webdriver_path

    def close_browser(self, profile_id):
        """
        Close the AdsPower browser for a given profile.

        Args:
            profile_id (str): The ID of the profile whose browser should be closed.
        """
        # Construct the URL for the API request to stop the browser for the given profile
        url = f"{self.base_url}/api/v1/browser/stop?user_id={profile_id}"
        response = requests.get(url)

        # Log the status of the browser closing operation
        logging.info(f"AdsPower Browser Close: {response.status_code}")

        # Raise an exception for failed requests (non-2xx status codes)
        response.raise_for_status()

    def delete_profile(self, profile_id):
        """
        Delete a profile from AdsPower.

        Args:
            profile_id (str): The ID of the profile to delete.
        """
        # Construct the URL and payload for the profile deletion request
        url = f"{self.base_url}/api/v1/user/delete"
        payload = {"user_ids": [profile_id]}

        response = requests.post(url, json=payload)

        # Log the status of the profile deletion operation
        logging.info(f"AdsPower Profile Deletion: {response.status_code}")

        # Raise an exception for failed requests (non-2xx status codes)
        response.raise_for_status()

        # Log the response from the API after profile deletion
        logging.info(f"Profile Deletion Response: {response.json()}")

    def get_cookies(self, profile_id):
        """
        Get cookies and user agent for a given profile.

        Args:
            profile_id (str): The ID of the profile to get cookies for.

        Returns:
            tuple: Cookie string and user agent.
        """
        # Fetch the WebSocket endpoint and webdriver path for the profile
        ws_endpoint, webdriver_path = self.get_ws_endpoint(profile_id)

        # Set up the Selenium WebDriver to use the WebSocket endpoint and webdriver path
        service = Service(executable_path=webdriver_path)
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", ws_endpoint)

        driver = webdriver.Chrome(service=service, options=options)

        # Log the start of the cookie retrieval process
        logging.info("Start Getting Cookies")

        try:
            # Open StubHub and wait for the page to load
            driver.get("https://www.stubhub.com/")

            # worst case, if the proxies are slow. We can replace with any element to load,
            # if we do not need to hardcode the wait time.
            time.sleep(10)

            # Get the cookies from the browser and convert them into a string
            cookies = driver.get_cookies()
            cookie_string = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

            # Get the user agent using JavaScript execution within the browser
            user_agent = driver.execute_script("return navigator.userAgent;")
        finally:
            # Close the browser after fetching cookies
            driver.quit()

        # Close the browser via API as well
        self.close_browser(profile_id)

        return cookie_string, user_agent
