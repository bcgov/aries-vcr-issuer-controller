from flask import jsonify, abort, request, make_response

import requests
import json
import os
import time
import yaml
import config
import uuid
import threading


# list of cred defs per schema name/version
app_config = {}
app_config['schemas'] = {}
synced = {}

class StartupProcessingThread(threading.Thread):
    def __init__(self, ENV):
        threading.Thread.__init__(self)
        self.ENV = ENV

    def run(self):
        # read configuration files
        config_root = self.ENV.get('CONFIG_ROOT', '../config')
        config_schemas = config.load_config(config_root + "/schemas.yml", env=self.ENV)
        config_services = config.load_config(config_root + "/services.yml", env=self.ENV)

        #print("schemas.yml -->", json.dumps(config_schemas))
        #print("services.yml -->", json.dumps(config_services))

        agent_admin_url = self.ENV.get('AGENT_ADMIN_URL')
        if not agent_admin_url:
            raise RuntimeError("Error AGENT_ADMIN_URL is not specified, can't connect to Agent.")
        app_config['AGENT_ADMIN_URL'] = agent_admin_url

        # ensure DID is registered
        ledger_url = self.ENV.get('LEDGER_URL')
        auto_register_did = self.ENV.get('AUTO_REGISTER_DID', False)
        if auto_register_did and ledger_url:
            # gt seed and alias to register
            seed = self.ENV.get('WALLET_SEED_VONX')
            alias = list(config_services['issuers'].keys())[0]

            # register DID
            response = requests.post(ledger_url+'/register', json.dumps({"alias": alias, "seed": seed, "role": "TRUST_ANCHOR"}))
            response.raise_for_status()
            did = response.json()
            print("Registered did", did)
            app_config['DID'] = did['did']
            time.sleep(5)

        # register schemas and credential definitions
        for schema in config_schemas:
            schema_name = schema['name']
            schema_version = schema['version']
            schema_attrs = []
            schema_descs = {}
            if isinstance(schema['attributes'], dict):
                # each element is a dict
                for attr, desc in schema['attributes'].items():
                    schema_attrs.append(attr)
                    schema_descs[attr] = desc
            else:
                # assume it's an array
                for attr in schema['attributes']:
                    schema_attrs.append(attr)

            # register our schema(s) and credential definition(s)
            schema_request = {"schema_name": schema_name, "schema_version": schema_version, "attributes": schema_attrs}
            response = requests.post(agent_admin_url+'/schemas', json.dumps(schema_request))
            response.raise_for_status()
            schema_id = response.json()
            app_config['schemas']['SCHEMA_' + schema_name] = schema
            app_config['schemas']['SCHEMA_' + schema_name + '_' + schema_version] = schema_id['schema_id']
            print("Registered schema", schema_id)

            cred_def_request = {"schema_id": schema_id['schema_id']}
            response = requests.post(agent_admin_url+'/credential-definitions', json.dumps(cred_def_request))
            response.raise_for_status()
            credential_definition_id = response.json()
            app_config['schemas']['CRED_DEF_' + schema_name + '_' + schema_version] = credential_definition_id['credential_definition_id']
            print("Registered credential definition", credential_definition_id)

        # what is the TOB connection name?
        tob_connection_params = config_services['verifiers']['bctob']

        # check if we have a TOB connection
        response = requests.get(agent_admin_url+'/connections')
        response.raise_for_status()
        connections = response.json()['results']
        tob_connection = None
        for connection in connections:
            # check for TOB connection
            if connection['their_label'] == tob_connection_params['alias']:
                tob_connection = connection

        if not tob_connection:
            # if no tob connection then establish one
            tob_agent_admin_url = tob_connection_params['connection']['agent_admin_url']
            if not tob_agent_admin_url:
                raise RuntimeError("Error TOB_AGENT_ADMIN_URL is not specified, can't establish a TOB connection.")

            response = requests.post(tob_agent_admin_url+'/connections/create-invitation')
            response.raise_for_status()
            invitation = response.json()

            response = requests.post(agent_admin_url+'/connections/receive-invitation', json.dumps(invitation['invitation']))
            response.raise_for_status()
            tob_connection = response.json()

            print("Established tob connection", tob_connection)
            time.sleep(5)

        app_config['TOB_CONNECTION'] = tob_connection['connection_id']
        synced[tob_connection['connection_id']] = False

        for issuer_name, issuer_info in config_services['issuers'].items():
            # register ourselves (issuer, schema(s), cred def(s)) with TOB
            issuer_config = {
                        "name": issuer_name,
                        "abbreviation": issuer_info['abbreviation'],
                        "did": app_config['DID'],
                        "email": issuer_info['email'],
                        "endpoint": issuer_info['endpoint'],
                        "label": "tbd",
                        "logo_path": None,  # TODO logo base 64
                        "url": issuer_info['url']
                    }
            credential_types = []
            for credential_type in issuer_info['credential_types']:
                schema_name = credential_type['schema']
                schema_info = app_config['schemas']['SCHEMA_' + schema_name]
                credential_type_info = {
                            "name": schema_info['name'],
                            "schema": schema_name,
                            "topic": credential_type['topic'],
                            "version": schema_info['version'],
                            #"cardinality_fields": {},  # TODO cardinality
                            #"category_labels": {},  # TODO what is this?
                            "credential": credential_type['credential'],
                            "credential_def_id": app_config['schemas']['CRED_DEF_' + schema_name + '_' + schema_info['version']],
                            "description": schema_info['description'],
                            "endpoint": credential_type['issuer_url'],
                            "logo_b64": None,  # TODO logo base 64
                            "mapping": credential_type['mapping'],
                            "visible_fields": []
                        }

                # config for each attribute
                if isinstance(schema_info['attributes'], dict):
                    credential_type_info['claim_labels'] = {}
                    credential_type_info['claim_descriptions'] = {}
                    # each element is a dict
                    for attr, desc in schema_info['attributes'].items():
                        for key, value in desc.items():
                            if '_' in key:
                                claim_label = None
                                label_lang = key.split('_', 1)
                                if label_lang[0] == 'label':
                                    claim_label = 'claim_labels'
                                elif label_lang[0] == 'description':
                                    claim_label = 'claim_descriptions'
                                if claim_label:
                                    if not attr in credential_type_info[claim_label]:
                                        credential_type_info[claim_label][attr] = {}
                                    credential_type_info[claim_label][attr][label_lang[1]] = value
                if 'cardinality_fields' in credential_type:
                    credential_type_info['cardinality_fields'] = credential_type['cardinality_fields']

                credential_types.append(credential_type_info)

            issuer_request = {
                "connection_id": app_config['TOB_CONNECTION'],
                "issuer_registration": {
                    "credential_types": credential_types,
                    "issuer": issuer_config
                }
            }
            #print("Registering issuer", json.dumps(issuer_request))

            response = requests.post(agent_admin_url+'/issuer_registration/send', json.dumps(issuer_request))
            response.raise_for_status()
            issuer_data = response.json()
            print("Registered issuer", issuer_name)

        synced[tob_connection['connection_id']] = True
        print("Connection {} is synchronized".format(tob_connection))


def startup_init(ENV):
    global app_config

    thread = StartupProcessingThread(ENV)
    thread.start()


credential_lock = threading.Lock()
credential_requests = {}
credential_responses = {}
credential_threads = {}

def set_credential_thread_id(cred_exch_id, thread_id):
    credential_lock.acquire()
    try:
        # add 2 records so we can x-ref
        credential_threads[thread_id] = cred_exch_id
        credential_threads[cred_exch_id] = thread_id
    finally:
        credential_lock.release()

def add_credential_request(cred_exch_id):
    credential_lock.acquire()
    try:
        result_available = threading.Event()
        credential_requests[cred_exch_id] = result_available
        return result_available
    finally:
        credential_lock.release()

def add_credential_response(cred_exch_id, response):
    credential_lock.acquire()
    try:
        credential_responses[cred_exch_id] = response
        if cred_exch_id in credential_requests:
            result_available = credential_requests[cred_exch_id]
            result_available.set()
            del credential_requests[cred_exch_id]
    finally:
        credential_lock.release()

def add_credential_problem_report(thread_id, response):
    if thread_id in credential_threads:
        cred_exch_id = credential_threads[thread_id]
        add_credential_response(cred_exch_id, response)

def get_credential_response(cred_exch_id):
    credential_lock.acquire()
    try:
        if cred_exch_id in credential_responses:
            response = credential_responses[cred_exch_id]
            del credential_responses[cred_exch_id]
            if cred_exch_id in credential_threads:
                thread_id = credential_threads[cred_exch_id]
                del credential_threads[cred_exch_id]
                del credential_threads[thread_id]
            return response
        else:
            return None
    finally:
        credential_lock.release()


TOPIC_CONNECTIONS = "connections"
TOPIC_CREDENTIALS = "credentials"
TOPIC_PRESENTATIONS = "presentations"
TOPIC_GET_ACTIVE_MENU = "get-active-menu"
TOPIC_PERFORM_MENU_ACTION = "perform-menu-action"
TOPIC_ISSUER_REGISTRATION = "issuer_registration"
TOPIC_PROBLEM_REPORT = "problem-report"


def handle_connections(state, message):
    # TODO auto-accept?
    print("handle_connections()", state)
    return jsonify({'message': state})

def handle_credentials(state, message):
    # TODO auto-respond to proof requests
    print("handle_credentials()", state, message['credential_exchange_id'])
    # TODO new "stored" state is being added by Nick
    if 'thread_id' in message:
        set_credential_thread_id(message['credential_exchange_id'], message['thread_id'])
    if state == 'stored':
        response = {'success': True, 'result': message['credential_exchange_id']}
        add_credential_response(message['credential_exchange_id'], response)
    return jsonify({'message': state})

def handle_presentations(state, message):
    # TODO auto-respond to proof requests
    print("handle_presentations()", state)
    return jsonify({'message': state})

def handle_get_active_menu(message):
    # TODO add/update issuer info?
    print("handle_get_active_menu()", message)
    return jsonify({})

def handle_perform_menu_action(message):
    # TODO add/update issuer info?
    print("handle_perform_menu_action()", message)
    return jsonify({})

def handle_register_issuer(message):
    # TODO add/update issuer info?
    print("handle_register_issuer()")
    return jsonify({})

def handle_problem_report(message):
    print("handle_problem_report()", message)
    if is_credential_error():
        # TODO set credential status
        # {
        #    '@type': 'did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/notification/1.0/problem-report', 
        #    '@id': '773a2a97-1831-40c7-ad26-e51d61eb3e1b', 
        #    '~thread': {'thid': '4100b3da-334d-4032-9c63-e884753965a5'}, 
        #    'explain-ltxt': 'Deliberately failed'
        # }
        response = {'success': False, 'result': message['explain-ltxt']}
        add_credential_problem_report(message['~thread']['thid'], response)

    return jsonify({})


class SendCredentialThread(threading.Thread):
    def __init__(self, credential_definition_id, cred_offer, url):
        threading.Thread.__init__(self)
        self.credential_definition_id = credential_definition_id
        self.cred_offer = cred_offer
        self.url = url

    def run(self):
        response = requests.post(self.url, json.dumps(self.cred_offer))
        response.raise_for_status()
        cred_data = response.json()
        print("cred_data after initial post:", cred_data)
        result_available = add_credential_request(cred_data['credential_exchange_id'])
        print("Sent offer", cred_data['credential_exchange_id'], cred_data['connection_id'])

        # wait for confirmation from the agent, which will include the credential exchange id
        result_available.wait()
        self.cred_response = get_credential_response(cred_data['credential_exchange_id'])
        print("Got response", self.cred_response)

def handle_send_credential(cred_input):
    """
    # other sample data
    sample_credentials = [
        {
            "schema": "ian-registration.ian-ville",
            "version": "1.0.0",
            "attributes": {
                "corp_num": "ABC12345",
                "registration_date": "2018-01-01", 
                "entity_name": "Ima Permit",
                "entity_name_effective": "2018-01-01", 
                "entity_status": "ACT", 
                "entity_status_effective": "2019-01-01",
                "entity_type": "ABC", 
                "registered_jurisdiction": "BC", 
                "effective_date": "2019-01-01",
                "expiry_date": ""
            }
        },
        {
            "schema": "ian-permit.ian-ville",
            "version": "1.0.0",
            "attributes": {
                "permit_id": str(uuid.uuid4()),
                "entity_name": "Ima Permit",
                "corp_num": "ABC12345",
                "permit_issued_date": "2018-01-01", 
                "permit_type": "ABC", 
                "permit_status": "OK", 
                "effective_date": "2019-01-01"
            }
        }
    ]
    """
    # construct and send the credential
    #print("Received credentials", cred_input)

    agent_admin_url = app_config['AGENT_ADMIN_URL']

    # let's send a credential!
    cred_responses = []
    for credential in cred_input:
        cred_def_key = 'CRED_DEF_' + credential['schema'] + '_' + credential['version']
        credential_definition_id = app_config['schemas'][cred_def_key]
        cred_offer = {
            "connection_id": app_config['TOB_CONNECTION'],
            "credential_definition_id": credential_definition_id,
            "credential_values": credential['attributes']
        }
        thread = SendCredentialThread(credential_definition_id, cred_offer, agent_admin_url+'/credential_exchange/send')
        thread.start()
        thread.join()
        cred_responses.append(thread.cred_response)

    return jsonify(cred_responses)
