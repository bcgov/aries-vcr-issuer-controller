#!/usr/bin/python
from configparser import ConfigParser
import os 
import urllib.parse

 
def config(filename='database.ini', section='postgresql'):
    db = {}
    if section == 'eao_data':
        db['host'] = os.environ.get('EAO_MDB_DB_HOST', 'localhost')
        db['port'] = os.environ.get('EAO_MDB_DB_PORT', '27017')
        db['database'] = os.environ.get('EAO_MDB_DB_DATABASE', 'eao_db')
        db['user'] = urllib.parse.quote_plus(os.environ.get('EAO_MDB_DB_USER', ''))
        db['password'] = urllib.parse.quote_plus(os.environ.get('EAO_MDB_DB_PASSWORD', ''))
    elif section == 'event_processor':
        db['host'] = os.environ.get('EVENT_PROC_DB_HOST', 'localhost')
        db['port'] = os.environ.get('EVENT_PROC_DB_PORT', '5444')
        db['database'] = os.environ.get('EVENT_PROC_DB_DATABASE', 'eao_locker_db')
        db['user'] = os.environ.get('EVENT_PROC_DB_USER', 'eao_locker_db')
        db['password'] = os.environ.get('EVENT_PROC_DB_PASSWORD', '')
    else:
        raise Exception('Section {0} not a valid database'.format(section))
 
    return db

