"""Internal functions used to process XBRL data received from the FFIEC Webservice
"""
from itertools import chain
import xmltodict
from datetime import datetime
import re

re_date = re.compile('[0-9]{4}\-[0-9]{2}\-[0-9]{2}')

def _process_xml(data: bytes, output_date_format: str):
    #data = zipfile_stream.open(first_file).read()
    dict_data = xmltodict.parse(data.decode('utf-8'))['xbrl']

    keys_to_parse = list(filter(lambda x: 'cc:' in x, dict_data.keys())) + list(filter(lambda x: 'uc:' in x, dict_data.keys()))
    parsed_data = list(chain.from_iterable(filter(None,list(map(lambda x: _process_xbrl_item(x, dict_data[x], output_date_format),keys_to_parse,)))))
    ret_data = []
    for row in parsed_data:
        new_dict = {}
        new_dict.update({'mdrm':row['mdrm']})
        new_dict.update({'rssd':row['rssd']})
        new_dict.update({'quarter':row['quarter']})
        if row['data_type'] == 'int':
            new_dict.update({'int_data':int(row['value'])})
            new_dict.update({'float_data':None})
            new_dict.update({'bool_data':None})
            new_dict.update({'str_data':None})
            new_dict.update({'data_type':row['data_type']})

        elif row['data_type'] == 'float':
            new_dict.update({'int_data':None})
            new_dict.update({'float_data':row['value']})
            new_dict.update({'bool_data':None})
            new_dict.update({'str_data':None})
            new_dict.update({'data_type':row['data_type']})

        elif row['data_type'] == 'str':
            new_dict.update({'int_data':None})
            new_dict.update({'float_data':None})
            new_dict.update({'bool_data':None})
            new_dict.update({'str_data':row['value']})
            new_dict.update({'data_type':row['data_type']})

        elif row['data_type'] == 'float':
            new_dict.update({'int_data':None})
            new_dict.update({'float_data':row['value']})
            new_dict.update({'bool_data':None})
            new_dict.update({'data_type':row['data_type']})
            new_dict.update({'str_data':None})

        elif row['data_type'] == 'bool':
            new_dict.update({'int_data':None})
            new_dict.update({'float_data':None})
            new_dict.update({'bool_data':row['value']})
            new_dict.update({'data_type':row['data_type']})
            new_dict.update({'str_data':None})

        ret_data.append(new_dict)
    
    return ret_data


def _create_ffiec_date_from_datetime(indate: datetime) -> str:
    """Converts a datetime object to a FFIEC-formatted date

    Args:
        indate (datetime): the date to convert

    Returns:
        str: the date in FFIEC format
    """
    month_str = str(indate.month)
    day_str = str(indate.day)
    year_str = str(indate.year)
    
    mmddyyyy = month_str + "/" + day_str + "/" + year_str
    
    return mmddyyyy

def _process_xbrl_item(name, items, date_format):
    # incoming is a data dictionary
    results = []
    if type(items) != list:
        items = [items]
    for j,item in enumerate(items):
        context = item.get('@contextRef')
        unit_type = item.get('@unitRef')
        value = item.get('#text')
        mdrm = name.replace("cc:","").replace("uc:","")
        rssd = context.split('_')[1]
        #date = int(context.split('_')[2].replace("-",''))

        quarter = re_date.findall(context)[0]

        # transform the date to the requested date format
        if date_format == 'string_original':
            quarter = _create_ffiec_date_from_datetime(datetime.strptime(quarter, '%Y-%m-%d'))
        elif date_format == 'string_yyyymmdd':
            quarter = datetime.strptime(quarter, '%Y-%m-%d').strftime('%Y%m%d')
        elif date_format == 'python_format':
            quarter = datetime.strptime(quarter, '%Y-%m-%d')
        
        data_type = None


        if unit_type == 'USD':
            value = int(value)/1000
            data_type = 'int'
        elif unit_type == 'PURE':
            value = float(value)
            data_type = 'float'
        elif unit_type == 'NON-MONETARY':
            value = float(value)
            data_type = 'float'
        elif value == 'true':
            value = True
            data_type = 'bool'
        elif value == 'false':
            value = False
            data_type = 'bool'
        else:
            data_type = 'str'                

        results.append({'mdrm':mdrm, 'rssd':rssd, 'value':value, 'data_type':data_type, 'quarter':quarter})

    return results
