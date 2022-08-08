import pytest
import os
import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, 'python')

from ffiec_data_connect import credentials
from ffiec_data_connect import ffiec_connection
from ffiec_data_connect import methods as m

"""Tests that require valid credentials to access the FFIEC webservice site
"""

def check_for_credentials():
    creds = credentials.WebserviceCredentials()
    if creds.username is None or creds.password is None:
        print("No credentials found. Please refer to the README.md file for instructions on how to set up the credentials file.")
        return False
    else:
        return True

def test_package_loading():
    if not check_for_credentials():
        sys.exit(1)
    
    creds = credentials.WebserviceCredentials()
    conn = ffiec_connection.FFIECConnection()
    conn.test_connection()
    creds.test_credentials(conn.session)
    
    return

def test_collect_reporting_periods():
    
    if not check_for_credentials():
        sys.exit(1)
    
    creds = credentials.WebserviceCredentials()
    conn = ffiec_connection.FFIECConnection()
    results = m.collect_reporting_periods(conn.session, creds)
    print(results)
    return

def test_collect_data():
    
    if not check_for_credentials():
        sys.exit(1)
    
    creds = credentials.WebserviceCredentials()
    conn = ffiec_connection.FFIECConnection()
    results = m.collect_data(conn.session, creds,reporting_period = "6/30/2010", rssd_id = '37', series='call')
    print(results)
    return
