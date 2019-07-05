#!/usr/bin/python
 
import psycopg2
from pymongo import MongoClient
from von_pipeline.config import config
from von_pipeline.eventprocessor import EventProcessor

 
with EventProcessor() as event_processor:
    event_processor.create_tables()
    print("Created event processor tables")

    print("TODO Create development mongodb schema")
    mdb_config = config(section='eao_data')
    print(mdb_config['host'], mdb_config['port'], mdb_config['database'])
    client = MongoClient('mongodb://%s:%s@%s:%s' % (mdb_config['user'], mdb_config['password'], mdb_config['host'], mdb_config['port']))
    db = client[mdb_config['database']]

    collection = db['test-collection']

