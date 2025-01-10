# StubHub Event Scraper with AdsPower

This script automates the process of scraping event data from [StubHub](https://www.stubhub.com/) for US states. It uses AdsPower to manage profiles and retrieve cookies, which are then used to make API requests for event listings. The script handles browser automation via AdsPower to get valid cookies that can be used for API scraping, ensuring seamless interaction with StubHub's platform.

## Prerequisites

- **Python 3.6+**: Make sure you have Python 3.6 or higher installed on your system.
- **Selenium WebDriver**: The script uses the Selenium WebDriver for interacting with browsers.
- **Requests Library**: Used to make HTTP requests to the AdsPower API and other services.

## Installation Steps

1. **Create a Virtual Environment**:
   - Navigate to your project folder in the terminal.
   - Run the following command to create a virtual environment:
     ```bash
     python3 -m venv venv
     ```

2. **Activate the Virtual Environment**:
   - On Linux/macOS:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

3. **Install Required Dependencies**:
   - Install all the dependencies listed in `requirements.txt` using pip:
     ```bash
     pip install -r requirements.txt
     ```

4. **Install Required Dependencies**:
   - Install all the dependencies listed in `requirements.txt` using pip:
     ```bash
     python scraper.py
     ```

5. **Download AdsPower**:
   - Download and install AdsPower from the [official AdsPower website](https://www.adspower.com/).
   - After installation, launch AdsPower and create a new account or use an existing one.

6. **Create Profiles**:
   - Log in to AdsPower and create profiles for your usage.
   - Set up proxies for each profile inside AdsPower and ensure each profile has a unique signature.
   - Make sure each profile is properly configured to work with the specific proxies.

## Configuration

### Setting Up `settings.py`

In the `settings.py` file, configure the following parameters:

1. **API Base URL**:
   - Set the AdsPower API URL (we can host Adspower easily on any VM and use that IP address here instead, but for local setup we can install adspower on local system and use their local APIs.):
     ```python
     ADSPOWER_BASE_URL = "http://local.adspower.com:50325"  # Change if necessary
     ```

2. **Profile to Proxy Mapping**:
   - Define the proxy mapping for each profile under `PROFILES_TO_PROXIES`. This mapping links each profile to a specific proxy with authentication credentials and a rotation URL:
   
   ```python
   PROFILES_TO_PROXIES = {
       # Profile identifier 'profile_id'
       # This profile is is mapped to a specific proxy with authentication and a rotation URL
       "************": {
           # Proxy URL, including authentication credentials
           "proxy": "http://**************************************",
           # Rotation URL for dynamically changing the proxy during requests
           "rotation_url": "http://**************************************"
       }
   }
