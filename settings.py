"""
Settings.py file for ProxyGPT. This file contains the settings for the API.

Author: Benjamin Klieger
Version: 0.1.1-beta
Date: 2024-01-05
License: MIT
"""

# ------------- [Settings] -------------

# Settings (Note: Both can be true and simultaneously active and enforced)
USE_HOURLY_RATE_LIMIT = True # Set to False to disable hourly rate limit
USE_DAILY_RATE_LIMIT = True # Set to False to disable daily rate limit

"""
Set INSECURE_DEBUG to False to disable debug mode. When debug mode is off,
server errors will no longer be passed through to the client, and instead 
present a generic error message to the API client, limiting the risk of 
exposing any secret variables stored on the server side to client.
"""
INSECURE_DEBUG = True

"""
Set the installed and used modules here. Removing a module from this list 
will skip the import in main.py. Note some modules are dependent on others.
"""
INSTALLED_MODULES = ["graphics","logging"]


# ------------- [Checks] -------------

# Check the dependencies of the installed modules
dependencies = {"graphics":["logging"],"logging":[]}

# Add the dependencies
for module in INSTALLED_MODULES:
    for dependency in dependencies[module]:
        if dependency not in INSTALLED_MODULES:
            INSTALLED_MODULES.append(dependency)