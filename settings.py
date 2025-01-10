# Base URL for AdsPower API
# This is the local instance of the AdsPower service running on a specific port
ADSPOWER_BASE_URL = "http://local.adspower.com:50325"

# Number of retry attempts for failed operations
# In case of failure, the system will retry the specified number of times before giving up
RETRY_ATTEMPTS = 3

# Dictionary mapping profile identifiers to proxies
# Each profile is associated with a proxy and a URL for rotating it
PROFILES_TO_PROXIES = {
    # Profile identifier 'some_id'
    # This profile is mapped to a specific proxy with authentication and a rotation URL
    "ksfmgej": {
        # Proxy URL, including authentication credentials
        "proxy": "http://L1L50NIY9AC7:EBjYU5ItUx@45.79.140.189:8574",
        # Rotation URL for dynamically changing the proxy during requests
        "rotation_url": "http://L1L50NIY9AC7:EBjYurosea"
    }
}
