#!/usr/bin/python
 
import datetime
import decimal
import hashlib
import json
import time
import traceback
import types
from enum import Enum

import pytz

import psycopg2
from bson import json_util
from bson.objectid import ObjectId
from pymongo import ASCENDING, MongoClient
from von_pipeline import pipeline_utils
from von_pipeline.config import config

EAO_SYSTEM_TYPE = 'EAO_EL'

site_credential = 'SITE'
site_schema = 'inspection-site.eao-evidence-locker'
site_version = '0.0.1'

inspc_credential = 'INSPC'
inspc_schema = 'safety-inspection.eao-evidence-locker'
inspc_version = '0.0.1'

obsvn_credential = 'OBSVN'
obsvn_schema = 'inspection-document.eao-evidence-locker'
obsvn_version = '0.0.1'

CORP_BATCH_SIZE = 3000

MIN_START_DATE = datetime.datetime(datetime.MINYEAR+1, 1, 1)
MAX_END_DATE   = datetime.datetime(datetime.MAXYEAR-1, 12, 31)
DATA_CONVERSION_DATE = datetime.datetime(2004, 3, 26)

# for now, we are in PST time
timezone = pytz.timezone("America/Los_Angeles")

MIN_START_DATE_TZ = timezone.localize(MIN_START_DATE)
MAX_END_DATE_TZ   = timezone.localize(MAX_END_DATE)
DATA_CONVERSION_DATE_TZ = timezone.localize(DATA_CONVERSION_DATE)

# custom encoder to convert wierd data types to strings
class CustomJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            try:
                tz_aware = timezone.localize(o)
                return tz_aware.astimezone(pytz.utc).isoformat()
            except (Exception) as error:
                if o.year <= datetime.MINYEAR+1:
                    return MIN_START_DATE_TZ.astimezone(pytz.utc).isoformat()
                elif o.year >= datetime.MAXYEAR-1:
                    return MAX_END_DATE_TZ.astimezone(pytz.utc).isoformat()
                return o.isoformat()
        if isinstance(o, (list, dict, str, int, float, bool, type(None))):
            return JSONEncoder.default(self, o)        
        if isinstance(o, decimal.Decimal):
            return (str(o) for o in [o])
        if isinstance(o, set):
            return list(o)
        if isinstance(o, map):
            return list(o)
        if isinstance(o, types.GeneratorType):
            ret = ""
            for s in next(o):
                ret = ret + str(s)
            return ret
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            try:
                tz_aware = timezone.localize(o)
                return tz_aware.astimezone(pytz.utc).isoformat()
            except (Exception) as error:
                if o.year <= datetime.MINYEAR+1:
                    return MIN_START_DATE_TZ.astimezone(pytz.utc).isoformat()
                elif o.year >= datetime.MAXYEAR-1:
                    return MAX_END_DATE_TZ.astimezone(pytz.utc).isoformat()
                return o.isoformat()
        return json.JSONEncoder.default(self, o)


# interface to Event Processor database
class EventProcessor:
    def __init__(self):
        try:
            params = config(section='event_processor')
            self.conn = psycopg2.connect(**params)
        except (Exception) as error:
            print(error)
            print(traceback.print_exc())
            self.conn = None
            raise

    def __del__(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
 
    # create our base processing tables
    def create_tables(self):
        """ create tables in the PostgreSQL database"""
        commands = (
            """
            CREATE TABLE IF NOT EXISTS LAST_EVENT (
                RECORD_ID SERIAL PRIMARY KEY,
                SYSTEM_TYPE_CD VARCHAR(255) NOT NULL, 
                COLLECTION VARCHAR(255) NOT NULL,
                OBJECT_DATE TIMESTAMP NOT NULL,
                ENTRY_DATE TIMESTAMP NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS le_stc ON LAST_EVENT 
            (SYSTEM_TYPE_CD);
            """,
            """
            CREATE TABLE IF NOT EXISTS EVENT_HISTORY_LOG (
                RECORD_ID SERIAL PRIMARY KEY,
                SYSTEM_TYPE_CD VARCHAR(255) NOT NULL, 
                COLLECTION VARCHAR(255) NOT NULL,
                PROJECT_ID VARCHAR(255) NOT NULL,
                PROJECT_NAME VARCHAR(255) NOT NULL,
                OBJECT_ID VARCHAR(255) NOT NULL,
                OBJECT_DATE TIMESTAMP NOT NULL,
                UPLOAD_DATE TIMESTAMP,
                UPLOAD_HASH VARCHAR(255),
                ENTRY_DATE TIMESTAMP NOT NULL,
                PROCESS_DATE TIMESTAMP,
                PROCESS_SUCCESS CHAR,
                PROCESS_MSG VARCHAR(255)
            )
            """,
            """
            -- Hit for counts and queries
            CREATE INDEX IF NOT EXISTS chl_pd_null ON EVENT_HISTORY_LOG 
            (PROCESS_DATE) WHERE PROCESS_DATE IS NULL;
            """,
            """
            -- Hit for query
            CREATE INDEX IF NOT EXISTS chl_ri_pd_null_asc ON EVENT_HISTORY_LOG 
            (RECORD_ID ASC, PROCESS_DATE) WHERE PROCESS_DATE IS NULL;	
            """,
            """
            ALTER TABLE EVENT_HISTORY_LOG
            SET (autovacuum_vacuum_scale_factor = 0.0);
            """,
            """ 
            ALTER TABLE EVENT_HISTORY_LOG
            SET (autovacuum_vacuum_threshold = 5000);
            """,
            """
            ALTER TABLE EVENT_HISTORY_LOG  
            SET (autovacuum_analyze_scale_factor = 0.0);
            """,
            """ 
            ALTER TABLE EVENT_HISTORY_LOG  
            SET (autovacuum_analyze_threshold = 5000);
            """,
            """ 
            REINDEX TABLE EVENT_HISTORY_LOG;
            """,
            """
            CREATE TABLE IF NOT EXISTS CREDENTIAL_LOG (
                RECORD_ID SERIAL PRIMARY KEY,
                SYSTEM_TYPE_CD VARCHAR(255) NOT NULL, 
                SOURCE_COLLECTION VARCHAR(255) NOT NULL,
                SOURCE_ID VARCHAR(255) NOT NULL,
                PROJECT_ID VARCHAR(255) NOT NULL,
                PROJECT_NAME VARCHAR(255) NOT NULL,
                CREDENTIAL_TYPE_CD VARCHAR(255) NOT NULL,
                CREDENTIAL_ID VARCHAR(255) NOT NULL,
                SCHEMA_NAME VARCHAR(255) NOT NULL,
                SCHEMA_VERSION VARCHAR(255) NOT NULL,
                CREDENTIAL_JSON JSON NOT NULL,
                CREDENTIAL_HASH VARCHAR(64) NOT NULL, 
                ENTRY_DATE TIMESTAMP NOT NULL,
                PROCESS_DATE TIMESTAMP,
                PROCESS_SUCCESS CHAR,
                PROCESS_MSG VARCHAR(255)
            )
            """,
            """
            -- Hit duplicate credentials
            CREATE UNIQUE INDEX IF NOT EXISTS cl_hash_index ON CREDENTIAL_LOG 
            (CREDENTIAL_HASH);
            """,
            """
            -- Hit for counts and queries
            CREATE INDEX IF NOT EXISTS cl_pd_null ON CREDENTIAL_LOG 
            (PROCESS_DATE) WHERE PROCESS_DATE IS NULL;
            """,
            """
            -- Hit for query
            CREATE INDEX IF NOT EXISTS cl_ri_pd_null_asc ON CREDENTIAL_LOG 
            (RECORD_ID ASC, PROCESS_DATE) WHERE PROCESS_DATE IS NULL;
            """,
            """
            -- Hit for counts
            CREATE INDEX IF NOT EXISTS cl_ps ON CREDENTIAL_LOG
            (process_success)
            """,
            """
            -- Hit for queries
            CREATE INDEX IF NOT EXISTS cl_ps_pd_desc ON CREDENTIAL_LOG
            (process_success, process_date DESC)
            """,
            """
            ALTER TABLE CREDENTIAL_LOG
            SET (autovacuum_vacuum_scale_factor = 0.0);
            """,
            """ 
            ALTER TABLE CREDENTIAL_LOG
            SET (autovacuum_vacuum_threshold = 5000);
            """,
            """
            ALTER TABLE CREDENTIAL_LOG  
            SET (autovacuum_analyze_scale_factor = 0.0);
            """,
            """ 
            ALTER TABLE CREDENTIAL_LOG  
            SET (autovacuum_analyze_threshold = 5000);
            """,
            """ 
            REINDEX TABLE CREDENTIAL_LOG;
            """
            )
        cur = None
        try:
            cur = self.conn.cursor()
            for command in commands:
                cur.execute(command)
            self.conn.commit()
            cur.close()
            cur = None
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            print(traceback.print_exc())
            raise
        finally:
            if cur is not None:
                cur.close()

    # record the last event processed
    def insert_processed_event(self, system_type, collection, object_date):
        """ insert a new event into the event table """
        sql = """INSERT INTO LAST_EVENT (SYSTEM_TYPE_CD, COLLECTION, OBJECT_DATE, ENTRY_DATE)
                 VALUES(%s, %s, %s, %s) RETURNING RECORD_ID;"""
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(sql, (system_type, collection, object_date, datetime.datetime.now(),))
            _record_id = cur.fetchone()[0]
            self.conn.commit()
            cur.close()
            cur = None
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            print(traceback.print_exc())
            raise
        finally:
            if cur is not None:
                cur.close()

    # get the id of the last event processed (of a specific collection)
    def get_last_processed_event(self, system_type, collection):
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("""SELECT RECORD_ID, SYSTEM_TYPE_CD, COLLECTION, OBJECT_DATE, ENTRY_DATE
                           FROM LAST_EVENT where SYSTEM_TYPE_CD = %s and COLLECTION = %s
                           ORDER BY OBJECT_DATE desc""", (system_type, collection,))
            row = cur.fetchone()
            cur.close()
            cur = None
            event = None
            if row is not None:
                event = {}
                event['RECORD_ID'] = row[0]
                event['SYSTEM_TYPE_CD'] = row[1]
                event['COLLECTION'] = row[2]
                event['OBJECT_DATE'] = row[3]
                event['ENTRY_DATE'] = row[4]
            return event
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            print(traceback.print_exc())
            raise
        finally:
            if cur is not None:
                cur.close()

    # get the last event processed timestamp
    def get_last_processed_event_date(self, system_type):
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("""SELECT max(object_date) FROM LAST_EVENT where SYSTEM_TYPE_CD = %s""", (system_type,))
            row = cur.fetchone()
            cur.close()
            cur = None
            prev_event = row[0]
            return prev_event
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            print(traceback.print_exc())
            raise
        finally:
            if cur is not None:
                cur.close()

    # insert data for one corp into the history table
    def insert_event_history_log(self, cur, system_type, collection, project_id, project_name, object_id, object_date, upload_date, upload_hash, process_date=None, process_success=None, process_msg=None):
        """ insert a new corps into the corps table """
        sql = """INSERT INTO EVENT_HISTORY_LOG 
                 (SYSTEM_TYPE_CD, COLLECTION, PROJECT_ID, PROJECT_NAME, OBJECT_ID, OBJECT_DATE, UPLOAD_DATE, UPLOAD_HASH, ENTRY_DATE,
                    PROCESS_DATE, PROCESS_SUCCESS, PROCESS_MSG)
                 VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING RECORD_ID;"""
        if process_date is None:
            process_date = datetime.datetime.now()
        if process_success is None:
            process_success = 'Y'
        if process_msg is None:
            process_msg = ''
        cur.execute(sql, (system_type, collection, project_id, project_name, object_id, object_date, upload_date, upload_hash, datetime.datetime.now(), process_date, process_success, process_msg))
        record_id = cur.fetchone()[0]
        return record_id

    # insert a generated JSON credential into our log
    def insert_json_credential(self, cur, system_cd, cred_type, cred_id, schema_name, schema_version, credential, source_collection, source_id, project_id, project_name):
        sql = """INSERT INTO CREDENTIAL_LOG (SYSTEM_TYPE_CD, CREDENTIAL_TYPE_CD, CREDENTIAL_ID, 
                SCHEMA_NAME, SCHEMA_VERSION, CREDENTIAL_JSON, CREDENTIAL_HASH, ENTRY_DATE, SOURCE_COLLECTION, SOURCE_ID, PROJECT_ID, PROJECT_NAME)
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING RECORD_ID;"""
        # create row(s) for corp creds json info
        cred_json = json.dumps(credential, cls=CustomJsonEncoder, sort_keys=True)
        cred_hash = hashlib.sha256(cred_json.encode('utf-8')).hexdigest()
        try:
            cur.execute("savepoint save_" + cred_type)
            cur.execute(sql, (system_cd, cred_type, cred_id, schema_name, schema_version, cred_json, cred_hash, datetime.datetime.now(), source_collection, source_id, project_id, project_name))
            return 1
        except Exception as e:
            # ignore duplicate hash ("duplicate key value violates unique constraint "cl_hash_index"")
            # re-raise all others
            stre = str(e)
            if "duplicate key value violates unique constraint" in stre and "cl_hash_index" in stre:
                print("Hash exception, skipping duplicate credential for corp:", corp_num, cred_type, cred_id, e)
                cur.execute("rollback to savepoint save_" + cred_type)
                #print(cred_json)
                return 0
            else:
                print(traceback.print_exc())
                raise

    def compare_dates(self, first_date, op, second_date, msg):
        if first_date is None:
            print(msg, "first date is None")
        if second_date is None:
            print(msg, "second date is None")
        if op == "==" or op == '=':
            return first_date == second_date
        elif op == "<=":
            return first_date <= second_date
        elif op == "<":
            return first_date < second_date
        elif op == ">":
            return first_date > second_date
        elif op == ">=":
            return first_date >= second_date
        print(msg, "invalid date op", op)
        return False

    # store credentials for the provided corp
    def store_credentials(self, cur, system_typ_cd, corp_cred, source_collection, source_id, project_id, project_name):
        cred_count = 0
        cred_count = cred_count + self.insert_json_credential(cur, system_typ_cd, corp_cred['cred_type'], corp_cred['id'], 
                                                        corp_cred['schema'], corp_cred['version'], corp_cred['credential'],
                                                        source_collection, source_id, project_id, project_name)
        return cred_count

    def build_credential_dict(self, cred_type, schema, version, cred_id, credential):
        cred = {}
        cred['cred_type'] = cred_type
        cred['schema'] = schema
        cred['version'] = version
        cred['credential'] = credential
        cred['id'] = cred_id
        return cred


    # generate a foundational site credential
    def generate_site_credential(self, site, effective_date):
        site_cred = {}
        site_cred['project_id'] = site['PROJECT_ID']
        site_cred['entity_type'] = site['PROJECT_TYPE']
        site_cred['project_name'] = site['PROJECT_NAME']
        site_cred['location'] = 'Vancouver'
        site_cred['entity_status'] = 'ACT'
        site_cred['effective_date'] = effective_date
        site_cred['registration_date'] = effective_date

        return self.build_credential_dict(site_credential, site_schema, site_version, site_cred['project_id'], site_cred)


    # find an (existing) credential for the site
    def find_site_credential(self, system_type, site):
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("""SELECT PROJECT_ID, PROJECT_NAME FROM CREDENTIAL_LOG 
                           where SYSTEM_TYPE_CD = %s and PROJECT_ID = %s and CREDENTIAL_TYPE_CD = %s""", 
                           (system_type, site['PROJECT_ID'], site_credential,))
            row = cur.fetchone()
            cur.close()
            cur = None
            if row is None:
                return None
            site_cred = {}
            site_cred['project_id'] = row[0]
            site_cred['project_name'] = row[1]
            return site_cred
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            print(traceback.print_exc())
            raise
        finally:
            if cur is not None:
                cur.close()


    # generate a site inspection credential
    def generate_inspection_credential(self, site, inspection):
        inspection_cred = {}
        inspection_cred['project_id'] = site['PROJECT_ID']
        inspection_cred['inspection_id'] = inspection['OBJECT_ID']
        inspection_cred['created_date'] = inspection['OBJECT_DATE']
        inspection_cred['updated_date'] = inspection['OBJECT_DATE']
        inspection_cred['hash_value'] = inspection['UPLOAD_HASH']
        inspection_cred['effective_date'] = inspection['OBJECT_DATE']
        inspection_cred['inspector_name'] = inspection['inspector_name']
        inspection_cred['inspector_email'] = inspection['inspector_email']

        return self.build_credential_dict(inspc_credential, inspc_schema, inspc_version, 
                                          str(inspection_cred['project_id']) + ':' + str(inspection_cred['inspection_id']), 
                                          inspection_cred)
                                          
    # generate a site inspection credential
    def generate_observation_credential(self, project_id, inspection_id, observation):
        observation_cred = {}
        observation_cred['project_id'] = project_id
        observation_cred['inspection_id'] = inspection_id
        observation_cred['document_id'] = observation['OBJECT_ID']
        observation_cred['created_date'] = observation['OBJECT_DATE']
        observation_cred['updated_date'] = observation['OBJECT_DATE']
        observation_cred['hash_value'] = observation['UPLOAD_HASH']
        observation_cred['effective_date'] = observation['OBJECT_DATE']
        observation_cred['requirement'] = observation['requirement']
        observation_cred['has_media'] = len(observation['media'])
        observation_cred['coordinates'] = observation['coordinates'] if 'coordinates' in observation else None

        return self.build_credential_dict(obsvn_credential, obsvn_schema, obsvn_version,
                                          str(observation_cred['project_id']) + ':' + str(observation_cred['inspection_id'] + ':' + str(observation_cred['document_id'])),
                                          observation_cred)


    # get all inspection info from mongo db
    def add_inspector_details(self, inspection):
        mdb_inspector = self.mdb_db['_User'].find_one( {'_id' : inspection['userId']} )
        inspection['inspector_name'] = mdb_inspector['firstName'] + ' ' + mdb_inspector['lastName']
        inspection['inspector_email'] = mdb_inspector['publicEmail']

        return inspection



    def max_collection_date(self, max_dates, collection, inspection_date):
        if not collection in max_dates:
            return inspection_date
        if inspection_date > max_dates[collection]:
            return inspection_date
        return max_dates[collection]


    def generate_all_credentials(self, obj_tree, save_to_db=True):
        creds = []
        max_dates = {}
        try:
            # maintain cursor for storing creds in postgresdb
            cur = self.conn.cursor()

            # process sites:
            for site in obj_tree:                

                # issue foundational credential / only if we don't have one yet
                site_cred = self.find_site_credential(EAO_SYSTEM_TYPE, site)
                if site_cred is None:
                    site_cred = self.generate_site_credential(site, site['OBJECT_DATE'])
                    if save_to_db:
                        self.store_credentials(cur, EAO_SYSTEM_TYPE, site_cred, 'Site', site['PROJECT_ID'], site['PROJECT_ID'], site['PROJECT_NAME'])
                    creds.append(site_cred)

                # process inspections:
                for inspection in site['inspections']:

                    # fetch inspector data from mongodb and generate credential
                    inspection = self.add_inspector_details(inspection)
                    cred = self.generate_inspection_credential(site, inspection)

                    # record the fact that we have processed this Inspection, and issue credential
                    if save_to_db:
                        inspection_rec_id = self.insert_event_history_log(cur, EAO_SYSTEM_TYPE, 'Inspection', site['PROJECT_ID'], site['PROJECT_NAME'], inspection['OBJECT_ID'], inspection['OBJECT_DATE'], inspection['UPLOAD_DATE'], inspection['UPLOAD_HASH'])
                        self.store_credentials(cur, EAO_SYSTEM_TYPE, cred, 'Inspection', inspection_rec_id, site['PROJECT_ID'], site['PROJECT_NAME'])

                    creds.append(cred)

                    # save max inspection date
                    max_dates['Inspection'] = self.max_collection_date(max_dates, 'Inspection', inspection['OBJECT_DATE'])

                    # process observations:
                    for observation in inspection['observations']:

                        # generate credential
                        cred = self.generate_observation_credential(site['PROJECT_ID'], inspection['OBJECT_ID'], observation)

                        # record the fact that we have processed this Observation, and issue credential
                        if save_to_db:
                            observation_rec_id = self.insert_event_history_log(cur, EAO_SYSTEM_TYPE, 'Observation', site['PROJECT_ID'], site['PROJECT_NAME'], observation['OBJECT_ID'], observation['OBJECT_DATE'], observation['UPLOAD_DATE'], observation['UPLOAD_HASH'])
                            self.store_credentials(cur, EAO_SYSTEM_TYPE, cred, 'Observation', observation_rec_id, site['PROJECT_ID'], site['PROJECT_NAME'])

                        creds.append(cred)


            self.conn.commit()
            cur.close()
            cur = None

            # record max dates processed
            if save_to_db:
                for collection in max_dates:
                    self.insert_processed_event(EAO_SYSTEM_TYPE, collection, max_dates[collection])
                
            return creds
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            print(traceback.print_exc())
            raise
        finally:
            if cur is not None:
                cur.close()


    # derive a project id from a name (determanistic)
    def project_name_to_id(self, project_name):
        # first 10 non-space chars
        subname = "".join(project_name.split()).upper()
        if 12 >= len(subname):
            return subname
        return subname[:12]


    # find all un-processed objects in mongo db
    def find_unprocessed_objects(self):
        unprocessed_objects = []

        for collection in MDB_COLLECTIONS:
            # find last processed date for this collection
            last_event = self.get_last_processed_event(EAO_SYSTEM_TYPE, collection)

            # return if evlocker_date is missing or null
            if last_event is None:
                unprocesseds = self.mdb_db[collection].find( { 'evlocker_date' : { "$exists" : False } } ).sort(MDB_OBJECT_DATE, ASCENDING)
            else:
                last_date = last_event['OBJECT_DATE']
                unprocesseds = self.mdb_db[collection].find({'$and': [{'evlocker_date': {"$exists": False}}, {MDB_OBJECT_DATE: {"$gt": last_date}}]}).sort(MDB_OBJECT_DATE, ASCENDING)

            # fetch unprocessed records
            for unprocessed in unprocesseds:
                todo_obj = {}
                todo_obj['SYSTEM_TYPE_CD'] = EAO_SYSTEM_TYPE
                if collection == 'Inspection':
                    todo_obj['PROJECT_ID'] = self.project_name_to_id(unprocessed['project'])
                    todo_obj['PROJECT_NAME'] = unprocessed['project']
                    todo_obj['userId'] = unprocessed['userId']
                elif collection == 'Observation':
                    todo_obj['observationId'] = unprocessed['_id']
                    todo_obj['inspectionId'] = unprocessed['inspectionId'] if 'inspectionId' in unprocessed else None
                    todo_obj['_p_inspection'] = unprocessed['_p_inspection'] if '_p_inspection' in unprocessed else None
                    todo_obj['title'] = unprocessed['title'] if 'title' in unprocessed else None
                    todo_obj['requirement'] = unprocessed['requirement'] if 'requirement' in unprocessed else None
                    todo_obj['coordinate'] = unprocessed['coordinate'] if 'coordinate' in unprocessed else None
                else:
                    # Photo, Audio, Video
                    todo_obj['observationId'] = unprocessed['observationId'] if 'observationId' in unprocessed else None
                    todo_obj['_p_observation'] = unprocessed['_p_observation'] if '_p_observation' in unprocessed else None
                
                todo_obj['COLLECTION'] = collection
                todo_obj['OBJECT_ID'] = unprocessed['_id']
                todo_obj['OBJECT_DATE'] = unprocessed[MDB_OBJECT_DATE]
                todo_obj['UPLOAD_DATE'] = unprocessed[MDB_OBJECT_DATE]
                unprocessed_objects.append(todo_obj)

        # fill in project info for all items
        for unprocessed_object in unprocessed_objects:
            if unprocessed_object['COLLECTION'] != 'Inspection' and ('_p_inspection' in unprocessed_object or 'inspectionId' in unprocessed_object): 
                inspection = self.mdb_db['Inspection'].find_one( { '$or': [{'_id' : unprocessed_object['inspectionId']}, {'id' : unprocessed_object['_p_inspection']}] } );
                if inspection is not None:
                    unprocessed_object['PROJECT_ID'] = inspection['project']
                    unprocessed_object['PROJECT_NAME'] = inspection['project']

        return unprocessed_objects

    # organize records in a hierarchy - Site | Inspection | Observation | Media
    def organize_unprocessed_objects(self, mongo_rows):   
        project_details = pipeline_utils.get_project_details()
        organized_objects = []

        inspections = pipeline_utils.filter_objects_by_collection(pipeline_utils.COLLECTION_TYPE.INSPECTION, mongo_rows)
        for inspection in inspections:
            epic_id = pipeline_utils.get_project_id(project_details, inspection['PROJECT_NAME'])
            epic_project_type = pipeline_utils.get_project_type(project_details, inspection['PROJECT_NAME'])

            # create site or use existing one, and attach inspection
            if epic_id in organized_objects:
                site_object = organized_objects.remove(epic_id)
            elif inspection['PROJECT_ID'] in organized_objects:
                site_object = organized_objects[inspection['PROJECT_ID']]
            else:
                site_object = None
            
            if site_object is None:
                site_object = {}
                site_object['PROJECT_ID'] = epic_id if epic_id is not None else inspection['PROJECT_ID']
                site_object['PROJECT_TYPE'] = epic_project_type if epic_project_type is not None else 'N.A.'
                site_object['PROJECT_NAME'] = inspection['PROJECT_NAME']
                site_object['inspections'] = []
                site_object['OBJECT_DATE'] = None
            
            inspection_object = inspection
            inspection_object['observations'] = []

            # delete redundant information
            del inspection_object['PROJECT_ID']
            del inspection_object['PROJECT_NAME']            

            # process observations for each inspection
            observations = pipeline_utils.filter_objects_by_type_and_id(pipeline_utils.COLLECTION_TYPE.OBSERVATION, inspection['OBJECT_ID'], mongo_rows)
            for observation in observations:
                observation_object = observation
                observation_object['media'] = pipeline_utils.filter_objects_by_type_and_id(pipeline_utils.COLLECTION_TYPE.MEDIA, observation['OBJECT_ID'], mongo_rows)
                inspection_object['observations'].append(observation_object)
            
            # add inspection to site
            site_object['inspections'].append(inspection_object)

            # update site date
            if site_object['OBJECT_DATE'] is None or inspection_object['OBJECT_DATE'] < site_object['OBJECT_DATE']:
                site_object['OBJECT_DATE'] = inspection_object['OBJECT_DATE']

            # add site to organized_objects
            organized_objects.append(site_object)

        return organized_objects


    # main entry point for data processing and credential generation job
    # process inbound data from the mongodb inspections database
    def process_event_queue(self):
        cur = None
        start_time = time.perf_counter()
        processing_time = 0
        max_processing_time = 10 * 60
        continue_loop = True
        max_batch_size = CORP_BATCH_SIZE
        saved_creds = 0

        # find all un-processed objects from mongodb
        mongo_rows = self.find_unprocessed_objects()
        print("Row count = ", len(mongo_rows))

        # add hashes to inspections, observations, media
        hashed_rows = pipeline_utils.add_record_hashes(mongo_rows)

        # organize by project/inspection/observation
        mongo_objects = self.organize_unprocessed_objects(hashed_rows)
        print("Object count = ", len(mongo_objects))

        # generate and save credentials
        creds = self.generate_all_credentials(mongo_objects)
        print("Generated cred count = ", len(creds))


        



    # main entry point for processing status job
    def display_event_processing_status(self):
        tables = ['event_history_log', 'credential_log']

        for table in tables:
            process_ct     = self.get_record_count(table, False)
            outstanding_ct = self.get_record_count(table, True)
            print('Table:', table, 'Processed:', process_ct, 'Outstanding:', outstanding_ct)

            sql = "select count(*) from " + table + " where process_success = 'N'"
            error_ct = self.get_sql_record_count(sql)
            print('      ', table, 'Process Errors:', error_ct)
            if 0 < error_ct:
                self.print_processing_errors(table)

    def get_outstanding_corps_record_count(self):
        return self.get_record_count('event_by_corp_filing')
        
    def get_outstanding_creds_record_count(self):
        return self.get_record_count('credential_log')
        
    def get_record_count(self, table, unprocessed=True):
        sql_ct_select = 'select count(*) from'
        sql_corp_ct_processed   = 'where process_date is not null'
        sql_corp_ct_outstanding = 'where process_date is null'

        if table == 'credential_log':
            sql_corp_ct_processed = sql_corp_ct_processed

        sql = sql_ct_select + ' ' + table + ' ' + (sql_corp_ct_outstanding if unprocessed else sql_corp_ct_processed)

        return self.get_sql_record_count(sql)

    def get_sql_record_count(self, sql):
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(sql)
            ct = cur.fetchone()[0]
            cur.close()
            cur = None
            return ct
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            print(traceback.print_exc())
            raise
        finally:
            if cur is not None:
                cur.close()
            cur = None

    def print_processing_errors(self, table):
        sql = """select * from """ + table + """
                 where process_success = 'N'
                 order by process_date DESC
                 limit 20"""
        rows = self.get_sql_rows(sql)
        print("       Recent errors:")
        print(rows)

    def get_sql_rows(self, sql):
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            desc = cursor.description
            column_names = [col[0] for col in desc]
            rows = [dict(zip(column_names, row))  
                for row in cursor]
            cursor.close()
            cursor = None
            return rows
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            print(traceback.print_exc())
            raise
        finally:
            if cursor is not None:
                cursor.close()
            cursor = None
