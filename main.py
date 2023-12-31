"""
Main.py file for ProxyGPT. This file contains the main code for the API.

Author: Benjamin Klieger
Version: 0.2.0-beta
Date: 2024-01-05
License: MIT
"""

# ------------- [Import Libraries] -------------

# Required libraries from FastAPI for API functionality
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security.api_key import APIKeyHeader, APIKey
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse

# Required libraries from Pydantic for API functionality
from pydantic import BaseModel
from typing import List

# Required for environment variables
import os

# Required for inspecting code
import inspect

# Import requests for making API calls
import requests

# Required for rate limiting with database and timestamps
import sqlite3
import time

# Required for printing styled log messages 
from utils import *


# ------------- [Settings] -------------

# Import settings from settings.py
from settings import *

# Check if settings are properly imported and set, raise exception if not
if USE_HOURLY_RATE_LIMIT==None or USE_DAILY_RATE_LIMIT==None or INSECURE_DEBUG==None or INSTALLED_MODULES==None:
    raise Exception("One or more of the settings are not set or have been removed. They are required for operation of ProxyGPT, unless the code has been modified.")

# Import the modules
if "graphics" in INSTALLED_MODULES:
    # Import graphics module
    from modules.graphics import *

    from fastapi.templating import Jinja2Templates
    from fastapi.responses import HTMLResponse
    from fastapi import Request

    templates = Jinja2Templates(directory="templates")

    graphics_installed_bool = True
else:
    graphics_installed_bool = False


if "logging" in INSTALLED_MODULES:
    # Import logging module
    from modules.logging import *

    # Import time which is needed
    import time

    logging_installed_bool = True
else:
    logging_installed_bool = False


# ------------- [Initialization: App] -------------

# Create FastAPI app
app = FastAPI(
    title="ProxyGPT",
    description="Lightweight wrapper for OpenAI python library. Add custom hourly and daily rate limits to API usage, and share OpenAI access with your development team without providing your secret key.",
    version="v0.2.0-beta",
)

# ------------- [Initialization: Env] -------------

# Set minimum length for secure key
MIN_LENGTH_FOR_SECURE_KEY = 5

# Set ProxyGPT API key securely from environment variable, either singular key or multiple keys
proxygpt_api_key = os.getenv("PROXYGPT_API_KEY")
proxygpt_api_keys = os.getenv("PROXYGPT_API_KEYS")

if proxygpt_api_keys is not None:
    # Get list of keys with comma seperated keys
    proxygpt_api_keys = proxygpt_api_keys.split(",")

# Initialization check
initialization_transcript = ""
critical_exist = False

# Check if the singular key is set
if proxygpt_api_key is None and proxygpt_api_keys is None:
    initialization_transcript += red_critical(f'[Critical] PROXYGPT_API_KEY environment variable is not set. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
    critical_exist = True

# If the singular key is set, check if it is strong
elif proxygpt_api_key is not None and len(proxygpt_api_key) < MIN_LENGTH_FOR_SECURE_KEY:
    initialization_transcript+= yellow_warning(f'[Warning] PROXYGPT_API_KEY environment variable is too short to be secure. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')

# Check if multiple keys are set, and if so, check if there exist more than 0 keys
elif proxygpt_api_keys is not None and len(proxygpt_api_keys) == 0:
    initialization_transcript += red_critical(f'[Critical] PROXYGPT_API_KEYS environment variable is set, but no keys were parsed. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
    critical_exist = True

# Check if multiple keys are set, and if so, check if they are strong
elif proxygpt_api_keys is not None:
    for key in proxygpt_api_keys:
        if len(key) < MIN_LENGTH_FOR_SECURE_KEY:
            initialization_transcript += yellow_warning(f'[Warning] PROXYGPT_API_KEYS environment variable contains a key that is too short to be secure. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')

# Set OpenAI API key securely from environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")

if USE_HOURLY_RATE_LIMIT:
    hourly_rate_limit = (os.getenv("PROXYGPT_HOURLY_RATE_LIMIT"))
if USE_DAILY_RATE_LIMIT:
    daily_rate_limit = (os.getenv("PROXYGPT_DAILY_RATE_LIMIT"))

# Check if the key is set
if openai_api_key is None:
    initialization_transcript += red_critical(f'[Critical] OPENAI_API_KEY environment variable is not set. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
    critical_exist = True

# If the key is set, check if it is valid
elif len(openai_api_key) <5:
    initialization_transcript += red_critical(f'[Critical] OPENAI_API_KEY environment variable is too short to be a working key. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
    critical_exist = True
elif openai_api_key.startswith("sk-")==False:
    initialization_transcript += red_critical(f'[Critical] OPENAI_API_KEY environment variable is not a valid secret key. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
    critical_exist = True

# Check if the rate limit(s) are set correctly
if USE_HOURLY_RATE_LIMIT:
    if hourly_rate_limit == None:
        initialization_transcript += red_critical(f'[Critical] PROXYGPT_HOURLY_RATE_LIMIT environment variable is not set. Please change the settings on line 16 of main.py if you do not wish to use an hourly rate limit. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
        critical_exist = True        
    elif hourly_rate_limit.isdigit() == False: # Will return False for floating point numbers
        initialization_transcript += red_critical(f'[Critical] PROXYGPT_HOURLY_RATE_LIMIT environment variable is not a valid integer. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
        critical_exist = True
    else:
        hourly_rate_limit = int(hourly_rate_limit)
        
if USE_DAILY_RATE_LIMIT:
    if daily_rate_limit == None:
        initialization_transcript += red_critical(f'[Critical] PROXYGPT_DAILY_RATE_LIMIT environment variable is not set. Please change the settings on line 16 of main.py if you do not wish to use an daily rate limit. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
        critical_exist = True        
    elif daily_rate_limit.isdigit() == False: # Will return False for floating point numbers
        initialization_transcript += red_critical(f'[Critical] PROXYGPT_DAILY_RATE_LIMIT environment variable is not a valid integer. (Line {inspect.currentframe().f_lineno} in {os.path.basename(__file__)})\n')
        critical_exist = True
    else:
        daily_rate_limit = int(daily_rate_limit)

# Print results of initialization check
print("Initialization check:")
print(initialization_transcript)    
if critical_exist:
    print(red_critical("Critical errors found in initialization check. Please fix them before deploying. If you are building the Docker image and have not yet set the environment variables, you may ignore this message."))
else:
    print(green_success("No critical errors found in initialization check."))


# ------------- [Initialization: DB] -------------

# Check if database is needed for rate limiting
if USE_HOURLY_RATE_LIMIT or USE_DAILY_RATE_LIMIT:
    # Use SQLITE database to store API usage
    # Create a table for API usage if it does not exist
    conn = sqlite3.connect('proxygpt.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS api_usage
                    (api_timestamp integer)''')
    conn.commit()
    conn.close()


# ------------- [Helper Functions] -------------

# Make function for adding API usage
def log_api_usage() -> None:
    """
    This function logs an instance of API usage to the SQLite database.
    It only logs the instance if the rate limit is enabled.
    """
    if USE_HOURLY_RATE_LIMIT or USE_DAILY_RATE_LIMIT:
        with sqlite3.connect('proxygpt.db') as conn:
            c = conn.cursor()
            c.execute("INSERT INTO api_usage VALUES (?)", (int(time.time()),))
            conn.commit()

# Make function for getting API usage (hourly)
def get_api_usage_from_last_hour() -> int:
    """
    This function returns the number of API calls to OpenAI in the last hour.
    """
    with sqlite3.connect('proxygpt.db') as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM api_usage WHERE api_timestamp > ?", (int(time.time())-3600,))
        return c.fetchone()[0]

# Make function for getting API usage (daily)
def get_api_usage_from_last_day() -> int:
    """
    This function returns the number of API calls to OpenAI in the last day.
    """
    with sqlite3.connect('proxygpt.db') as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM api_usage WHERE api_timestamp > ?", (int(time.time())-86400,))
        return c.fetchone()[0]

# Make function for checking rate limit
def check_rate_limit() -> bool:
    """
    This function checks if the rate limit has been reached.

    Note that both hourly and daily rate limits can simultaneously be 
    in effect.

    Returns:
        bool: True if rate limit has not been reached, False otherwise.
    """
    if USE_HOURLY_RATE_LIMIT and get_api_usage_from_last_hour() >= hourly_rate_limit:
        return False
    if USE_DAILY_RATE_LIMIT and get_api_usage_from_last_day() >= daily_rate_limit:
        return False
    else:
        return True


# ------------- [Classes and Other] -------------

# Define a model of ChatMessage
class ChatMessage(BaseModel):
    role: str
    content: str

# Define a security scheme for API key
bearer_scheme = HTTPBearer()

# Define validation function for API key
def valid_api_key(api_key_header: APIKey = Depends(bearer_scheme)):

    if proxygpt_api_key:
        # Check if API key is valid
        if api_key_header.credentials != proxygpt_api_key:
            raise HTTPException(
                status_code=400, detail="Invalid API key"
            )
        return api_key_header.credentials
    else:
        # Check if API key is valid
        if api_key_header.credentials not in proxygpt_api_keys:
            raise HTTPException(
                status_code=400, detail="Invalid API key"
            )
        return api_key_header.credentials

# Define validation function for API key with rate limit
def valid_api_key_rate_limit(api_key_header: APIKey = Depends(bearer_scheme)):
    # Check if rate limit has been reached
    if check_rate_limit() == False:
        raise HTTPException(status_code=429, detail="Rate limit reached. Try again later. See /ratelimit to view status and settings.")

    if proxygpt_api_key:
        # Check if API key is valid
        if api_key_header.credentials != proxygpt_api_key:
            raise HTTPException(
                status_code=400, detail="Invalid API key"
            )
        return api_key_header.credentials
    else:
        # Check if API key is valid
        if api_key_header.credentials not in proxygpt_api_keys:
            raise HTTPException(
                status_code=400, detail="Invalid API key"
            )
        return api_key_header.credentials

# ------------- [Routes and Endpoints] -------------

@app.post('/api/openai/completions/gpt3')
async def get_openai_gpt3_completion(message: List[ChatMessage], temperature: float, api_key: str = Depends(valid_api_key_rate_limit)):
    """
    This endpoint allows you to interact with OpenAI's GPT-3 model for Chat Completion.

    - **message**: A list of message objects. Each object should have a "role" (which can be "system", "user", or "assistant") and a "content" (which is the actual content of the message).
    - **temperature**: The temperature to use for the model's response.

    The endpoint will return a string containing the model's response.
    """

    try:
        # Log API usage. Note, you could move this to the end of the endpoint and check the response content if you want to log only successful requests.
        log_api_usage()

        # Log time if logging installed.
        if logging_installed_bool:
            start_time = time.time()

        # Send request to OpenAI
        url = "https://api.openai.com/v1/chat/completions"
        payload = { "model": "gpt-3.5-turbo", "messages": [{"role": msg.role, "content": msg.content} for msg in message], "temperature": temperature }

        headers = {
            "content-type": "application/json",
            "Authorization": "Bearer " + str(openai_api_key)
        }

        # Send the request
        response = requests.post(url, json=payload, headers=headers)
        
        # Log API results if logging installed.
        if logging_installed_bool:
            insert_api_log(response_time=round((time.time()-start_time)*1000),response_code=response.status_code,endpoint=url,request=str(payload),response_str=response.text)

        return JSONResponse(status_code=200, content={"message": response.json()})
    except Exception as e:
        if INSECURE_DEBUG:
            return JSONResponse(status_code=500, content={"error": str(e)})
        else:
            print(e)
            return JSONResponse(status_code=500, content={"error": "Internal server error. Set INSECURE_DEBUG to True to view error details from client side."})


# Define a route for the GET of /ratelimit
@app.get('/ratelimit')
async def get_ratelimit(api_key: str = Depends(valid_api_key)):
    """
    This endpoint allows you to view the current rate limit status and settings.
    """

    # Return rate limit status and settings if rate limits are enabled
    json_to_return = {}
    if USE_DAILY_RATE_LIMIT:
        json_to_return["daily_rate_limit"] = daily_rate_limit
        json_to_return["daily_api_usage"] = get_api_usage_from_last_day()
    if USE_HOURLY_RATE_LIMIT:
        json_to_return["hourly_rate_limit"] = hourly_rate_limit
        json_to_return["hourly_api_usage"] = get_api_usage_from_last_hour()
    if len(json_to_return) == 0:
        json_to_return = {"error": "Rate limit is not enabled."}

    return JSONResponse(status_code=200, content=json_to_return)


if graphics_installed_bool:
    @app.get("/dashboard", response_class=HTMLResponse)
    async def get_dashboard(request: Request):
        """
        This endpoint allows you to view the dashboard of ProxyGPT.
        """

        return templates.TemplateResponse(
        "dashboard.html",
        {"request": request})

    @app.get("/dashboard-data")
    async def get_dashboard_data(api_key: str = Depends(valid_api_key)):
        """
        This endpoint allows you to view the dashboard data of ProxyGPT.
        """
        #TODO: clean logs to remove injection vulnerabilities

        log_results = transform_api_logs(get_api_logs())

        # Reverse
        log_results.reverse()

        return JSONResponse(status_code=200, content=log_results)