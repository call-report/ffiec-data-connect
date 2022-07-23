from datetime import datetime
import pytest
import os
import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, 'python')


import methods as m


"""Tests for testing various data transformations and other auxiliary functions"""

## Test the transformation of a reporting period to a date
def test_quarter_to_ffiec_date():
    test1 = "2Q2020"
    test2 = "3Q2021"
    test3 = "1Q2001"
    test4 = "4Q2003"
    test5 = "6/30/2010"
    test6 = "03/31/2020"
    test7 = "2020-03-31"
    test8 = "20200630"
    test9 = "20101231"
    resp1 = m.return_ffiec_reporting_date(test1)
    resp2 = m.return_ffiec_reporting_date(test2)
    resp3 = m.return_ffiec_reporting_date(test3)
    resp4 = m.return_ffiec_reporting_date(test4)
    resp5 = m.return_ffiec_reporting_date(test5)
    resp6 = m.return_ffiec_reporting_date(test6)
    resp7 = m.return_ffiec_reporting_date(test7)
    resp8 = m.return_ffiec_reporting_date(test8)
    resp9 = m.return_ffiec_reporting_date(test9)
    
    assert(resp1 == "6/30/2020")
    assert(resp2 == "9/30/2021")
    assert(resp3 == "3/31/2001")
    assert(resp4 == "12/31/2003")
    assert(resp5 == "6/30/2010")
    assert(resp6 == "3/31/2020")
    assert(resp7 == "3/31/2020")
    assert(resp8 == "6/30/2020")
    assert(resp9 == "12/31/2010")
    
    
    return
    
## test conversions of dates to ffiec formats

def test_convert_date_to_ffiec_format():
    test1 = "6/1/2010"
    test2 = "3/31/2020"
    test3 = "2020-03-31"
    test4 = "20200630"
    test5 = "20101231"
    test6 = datetime(2020, 3, 20)
    test7 = datetime(2011, 11, 11)
    resp1 = m.convert_any_date_to_ffiec_format(test1)
    resp2 = m.convert_any_date_to_ffiec_format(test2)
    resp3 = m.convert_any_date_to_ffiec_format(test3)
    resp4 = m.convert_any_date_to_ffiec_format(test4)
    resp5 = m.convert_any_date_to_ffiec_format(test5)
    resp6 = m.convert_any_date_to_ffiec_format(test6)
    resp7 = m.convert_any_date_to_ffiec_format(test7)
    assert(resp1 == "6/1/2010")
    assert(resp2 == "3/31/2020")
    assert(resp3 == "3/31/2020")
    assert(resp4 == "6/30/2020")
    assert(resp5 == "12/31/2010")
    assert(resp6 == "3/20/2020")
    assert(resp7 == "11/11/2011")
    return

def test_convert_quarter_to_date():
    test1 = "2Q2020"
    test2 = "3Q2021"
    test3 = "1Q2001"
    test4 = "4Q2003"
    
    resp1 = m.convert_quarter_to_date(test1)
    resp2 = m.convert_quarter_to_date(test2)
    resp3 = m.convert_quarter_to_date(test3)
    resp4 = m.convert_quarter_to_date(test4)
    
    assert(resp1 == datetime(2020, 6, 30))
    assert(resp2 == datetime(2021, 9, 30))
    assert(resp3 == datetime(2001, 3, 31))
    assert(resp4 == datetime(2003, 12, 31))
    
def test_is_valid_date_or_quarter():
    test1 = "2Q2020"
    test2 = datetime(2010,9,30)
    test3 = "2021-09-30"
    test4 = "20210230"
    test5 = "2021-12-30"
    
    test6 = "2/2/2022"
    test7 = "2010-08-10"
    test8 = "Q22022"
    
    resp1 = m.is_valid_date_or_quarter(test1)
    resp2 = m.is_valid_date_or_quarter(test2)
    resp3 = m.is_valid_date_or_quarter(test3)
    resp4 = m.is_valid_date_or_quarter(test4)
    resp5 = m.is_valid_date_or_quarter(test5)
    resp6 = m.is_valid_date_or_quarter(test6)
    resp7 = m.is_valid_date_or_quarter(test7)
    resp8 = m.is_valid_date_or_quarter(test8)
    
    assert(resp1 == True)
    assert(resp2 == True)
    assert(resp3 == True)
    assert(resp4 == True)
    
    assert(resp5 == True)
    assert(resp6 == True)
    assert(resp7 == True)
    
    assert(resp8 == False)
    
## todo, test the conversion of results