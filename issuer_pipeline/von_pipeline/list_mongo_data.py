#!/usr/bin/python
import psycopg2
from pymongo import MongoClient
import datetime
import json

from von_pipeline.config import config
from von_pipeline.eventprocessor import EventProcessor, CustomJsonEncoder


with EventProcessor() as eao_pipeline:
    objects = eao_pipeline.find_unprocessed_objects()
    obj_tree = eao_pipeline.organize_unprocessed_objects(objects)

    print(json.dumps(objects, cls=CustomJsonEncoder))
    print(json.dumps(obj_tree, cls=CustomJsonEncoder))

