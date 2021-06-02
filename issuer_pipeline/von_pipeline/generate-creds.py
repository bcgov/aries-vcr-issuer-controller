#!/usr/bin/python
import psycopg2
import datetime
import os
from von_pipeline.config import config
from von_pipeline.eventprocessor import EventProcessor


INIT_SEED = os.getenv("INIT_SEED")
GEN_TOPIC_COUNT = int(os.getenv("TOPIC_COUNT", "100"))

with EventProcessor() as event_processor:
    event_processor.process_event_queue(seed=INIT_SEED, topic_count=GEN_TOPIC_COUNT)
