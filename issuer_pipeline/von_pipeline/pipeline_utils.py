import hashlib
import json
from enum import Enum

import requests

from bson import json_util


class COLLECTION_TYPE(Enum):
    INSPECTION = 'Inspection'
    OBSERVATION = 'Observation'
    MEDIA = 'Media'

'''Adds the UPLOAD_HASH field to all the records, following this logic:
   - for each media object (Audio, Photo, Video) add the hash of the object itself
   - for each observation, add the field MEDIA_HASHES containing the list of related media hashes (sorted by OBJECT_ID)
     and then the hash of the resulting object
   - for each inspection add the hash resulting from the list of related observations (sorted by OBJECT_ID)

Returns:
  list -- The list of objects with added UPLOAD_HASH
'''
def add_record_hashes(object_list):
    # hash the content of each media object
    media_objects = filter_objects_by_collection(COLLECTION_TYPE.MEDIA, object_list)
    print('Generating hashes for ', len(media_objects), ' media objects')
    for media in media_objects:
        media['UPLOAD_HASH'] = generate_sha256_hash(media)
    
    # create the observation hash off of the hashes of related media objects
    observations = filter_objects_by_collection(COLLECTION_TYPE.OBSERVATION, object_list)
    print('Generating hashes for ', len(observations), ' observations')
    for observation in observations:
        related_media = filter_objects_by_type_and_id(COLLECTION_TYPE.MEDIA, observation['OBJECT_ID'], object_list)
        # sort by object id for consistency
        related_media = sorted(related_media, key=lambda media: media['OBJECT_ID'])
        hash_list = []
        
        for media in related_media:
            hash_list.append(media['UPLOAD_HASH'])
        
        observation['MEDIA_HASHES'] = hash_list
        observation['UPLOAD_HASH'] = generate_sha256_hash(hash_list)
    
    # create the inspection hash off of the hashes of related media objects
    inspections = filter_objects_by_collection(COLLECTION_TYPE.INSPECTION, object_list)
    print('Generating hashes for ', len(inspections), ' inspections')
    for inspection in inspections:
        observations = filter_objects_by_type_and_id(COLLECTION_TYPE.OBSERVATION, inspection['OBJECT_ID'], object_list)
        # sort by object id for consistency
        observations = sorted(observations, key=lambda observation: observation['OBJECT_ID'])
        hash_list = []
        
        for observation in observations:
            hash_list.append(observation['UPLOAD_HASH'])
        
        inspection['UPLOAD_HASH'] = generate_sha256_hash(hash_list)
    
    return object_list

'''Takes an object as input and returns the corresponding sha256 hash.

Returns:
    String -- The sha256 hash for the input object.
'''
def generate_sha256_hash(obj):
    string_rep = json.dumps(obj, default=json_util.default)
    string_rep = string_rep.encode('utf-8')

    return hashlib.sha256(string_rep).hexdigest()

'''Filters a list of objects based on the specified type and the specified (parent) id.

Returns:
  list -- the list of filtered objects
'''
def filter_objects_by_type_and_id(object_type: COLLECTION_TYPE, object_id: str, objects):
    item_list = []
    filter_key = None
    if object_type == COLLECTION_TYPE.OBSERVATION:
        filter_key = '_p_inspection'
    elif object_type == COLLECTION_TYPE.MEDIA:
        filter_key = '_p_observation'
    else:
        pass

    for item in objects:
        if filter_key in item and item[filter_key] is not None and item[filter_key].endswith(object_id):
            item_list.append(item)
    
    return item_list

'''Filters a list of objects based on the specified collection type.

Returns:
  list -- The filtered list of objects
'''
def filter_objects_by_collection(collection_type: COLLECTION_TYPE, objects):
    filtered_objects = []

    for item in objects:
        if item['COLLECTION'] == collection_type.value:
            filtered_objects.append(item)
        elif collection_type == COLLECTION_TYPE.MEDIA and item['COLLECTION'] in ['Audio', 'Photo', 'Video']:
            filtered_objects.append(item)
        else:
            pass
    
    return filtered_objects

'''Queries the EPIC public API exposing the project details

Returns:
    dict -- A dict containing the project details
'''
def get_project_details():
    # url = 'https://projects.eao.gov.bc.ca/api/projects/published'

    # response = requests.get(url)

    # return response.json()

    with open('von_pipeline/epic-projects.json', 'r') as f:
        return json.load(f)

def get_project_id(project_details: dict, project_name: str):
    detail = [x for x in project_details if x['name'] == project_name]
    result = None

    if len(detail) > 1:
      raise Exception('More than one project detail was found for ', project_name)
    elif len(detail) > 0:
      result = detail[0]['code']
    
    return result

def get_project_type(project_details: dict, project_name: str):
    detail = [x for x in project_details if x['name'] == project_name]
    result = None

    if len(detail) > 1:
      raise Exception('More than one project detail was found for ', project_name)
    elif len(detail) > 0:
      result = detail[0]['type']
    
    return result
