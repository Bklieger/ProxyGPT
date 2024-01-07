"""
Logging.py file for ProxyGPT. This file contains the logging module code for the API.

Author: Benjamin Klieger
Version: 0.2.0-beta
Date: 2024-01-05
License: MIT
"""

# ------------- [Import Libraries] -------------

# Required libraries from Pydantic for API functionality
from pydantic import BaseModel
from typing import List

# Required for inspecting code
import inspect

# Required for rate limiting with database and timestamps
import sqlite3
import time

# Required for printing styled log messages 
from utils import *


# ------------- [Initialization: DB] -------------

# Use SQLITE database to store API logs
# Create a table for API usage if it does not exist
conn = sqlite3.connect('proxygpt.db')
c = conn.cursor()

# Create the api_logs table with the new schema
c.execute('''
    CREATE TABLE IF NOT EXISTS api_logs (
        api_timestamp INTEGER,
        response_time FLOAT,
        response_code INTEGER,
        endpoint TEXT,
        request TEXT,
        response_str TEXT
    )
''')

# Commit the changes and close the connection
conn.commit()
conn.close()


# ------------- [Helper Functions] -------------

def get_last_n(list_to_cut: List[BaseModel], n: int) -> List[BaseModel]:
    """
    This function returns the last n number of items from a list.
    If n is None, the function returns the entire list.

    Args:
        list_to_cut (List[BaseModel]): The list to cut.
        n (int): The number of items to return.
    
    Returns:
        List[BaseModel]: The last n number of items from the list.
    """

    # If n is None, return the entire list
    if n is None:
        return list_to_cut
    # Otherwise, return the last n number of items from the list
    else:
        return list_to_cut[-n:]


# ------------- [Functions] -------------

# Function for inserting API log
def insert_api_log(response_time: float, response_code: int, endpoint: str, request: str, response_str: str) -> None:
    """
    This function inserts an instance of API usage into the SQLite database.

    Args:
        response_time (float): The response time of the API call.
        response_code (int): The response code of the API call.
        endpoint (str): The endpoint url of the API call.
        request (str) (optional): The request data of the API call.
        response_str (str) (optional): The response string of the API call.
    """

    conn = sqlite3.connect('proxygpt.db')
    c = conn.cursor()

    # Using parameterized query for safe insertion
    c.execute('''
        INSERT INTO api_logs (api_timestamp, response_time, response_code, endpoint, request, response_str)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (int(time.time()), response_time, response_code, endpoint, request, response_str))

    conn.commit()
    conn.close()


# Function to returning the API logs
def get_api_logs(start_time: int = None, end_time: int = None, last_n: int = None) -> List[BaseModel]:
    """
    This function returns a list of API logs from the SQLite database.

    Args:
        start_time (int) (optional): The start time of the API logs to return.
        end_time (int) (optional): The end time of the API logs to return.
        last_n (int) (optional): The last n number of API logs to return (will 
            select from filtered list if start_time and/or end_time are provided).

    Returns:
        List[BaseModel]: A list of API logs.
    """

    conn = sqlite3.connect('proxygpt.db')
    c = conn.cursor()

    # If start_time and end_time are provided, filter the logs by time
    if start_time and end_time:
        c.execute('''
            SELECT * FROM api_logs WHERE api_timestamp BETWEEN ? AND ?
        ''', (start_time, end_time))
    # If only start_time is provided, filter the logs by time
    elif start_time:
        c.execute('''
            SELECT * FROM api_logs WHERE api_timestamp >= ?
        ''', (start_time,))
    # If only end_time is provided, filter the logs by time
    elif end_time:
        c.execute('''
            SELECT * FROM api_logs WHERE api_timestamp <= ?
        ''', (end_time,))
    # If no time parameters are provided, select all logs
    else:
        c.execute('''
            SELECT * FROM api_logs
        ''')
    
    # Get the results from the query
    results = c.fetchall()

    # Filter by n, which will make no modification if n is None
    results = get_last_n(results, last_n)

    # Close the connection
    conn.close()
    
    # Return the results
    return results

# Function for transforming list of API logs into list of dictionaries
def transform_api_logs(logs: List[BaseModel]) -> List[BaseModel]:
    """
    This function transforms a list of API logs into a list of dictionaries.

    Args:  
        logs (List[BaseModel]): A list of API logs.

    Returns:
        List[BaseModel]: A list of API logs.
    """

    transformed_logs = []
    for log in logs:
        transformed_log = {
            "timestamp": log[0],
            "response_time": log[1],
            "response_code": log[2],
            "endpoint": log[3],
            "request": log[4],
            "response": log[5]
        }
        transformed_logs.append(transformed_log)

    return transformed_logs