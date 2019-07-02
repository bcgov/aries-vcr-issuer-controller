from flask import jsonify, abort, request, make_response, request

import requests
import json
import os
import time
import yaml
import config
import uuid


# list of cred defs per schema name/version
app_config = {}
app_config['schemas'] = {}

def startup_init(ENV):
    global app_config

    # read configuration files
    config_root = ENV.get('CONFIG_ROOT', '../config')
    config_schemas = config.load_config(config_root + "/schemas.yml", env=ENV)
    config_services = config.load_config(config_root + "/services.yml", env=ENV)

    print("schemas.yml -->", json.dumps(config_schemas))
    print("services.yml -->", json.dumps(config_services))

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
                "entity_status": "OK", 
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

    agent_admin_url = ENV.get('AGENT_ADMIN_URL')
    if not agent_admin_url:
        raise RuntimeError("Error AGENT_ADMIN_URL is not specified, can't connect to Agent.")

    # ensure DID is registered
    ledger_url = ENV.get('LEDGER_URL')
    auto_register_did = ENV.get('AUTO_REGISTER_DID', False)
    if auto_register_did and ledger_url:
        # gt seed and alias to register
        seed = ENV.get('WALLET_SEED_VONX')
        alias = list(config_services['issuers'].keys())[0]

        # register DID
        response = requests.post(ledger_url+'/register', json.dumps({"alias": alias, "seed": seed, "role": "TRUST_ANCHOR"}))
        response.raise_for_status()
        did = response.json()
        print("Registered did", did)
        app_config['DID'] = did['did']

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

    for issuer_name, issuer_info in config_services['issuers'].items():
        # register ourselves (issuer, schema(s), cred def(s)) with TOB
        issuer_config = {
                    "name": issuer_name,
                    "abbreviation": issuer_info['abbreviation'],
                    "did": app_config['DID'],
                    "email": issuer_info['email'],
                    "endpoint": issuer_info['endpoint'],
                    "label": "tbd",
                    "logo_path": issuer_info['logo_path'],
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
                        "cardinality_fields": {},
                        "category_labels": {},
                        "claim_descriptions": {},
                        "claim_labels": {},
                        "credential": credential_type['credential'],
                        "credential_def_id": app_config['schemas']['CRED_DEF_' + schema_name + '_' + schema_info['version']],
                        "description": schema_info['description'],
                        "endpoint": credential_type['issuer_url'],
                        "logo_b64": issuer_info['logo_path'],
                        "mapping": credential_type['mapping'],
                        "visible_fields": []
                    }

            # config for each attribute
            if isinstance(schema_info['attributes'], dict):
                # each element is a dict
                for attr, desc in schema_info['attributes'].items():
                    if 'label_en' in desc:
                        credential_type_info['claim_labels'][attr] = desc['label_en']
                    if 'description_en' in desc:
                        credential_type_info['claim_descriptions'][attr] = desc['description_en']
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
        print("Registering issuer", json.dumps(issuer_request))

        response = requests.post(agent_admin_url+'/issuer_registration/send', json.dumps(issuer_request))
        response.raise_for_status()
        issuer_data = response.json()
        print("Registered issuer", issuer_name)

    # let's send a credential!
    for sample_credential in sample_credentials:
        credential_definition_id = app_config['schemas']['CRED_DEF_' + sample_credential['schema'] + '_' + sample_credential['version']]
        cred_offer = {
            "connection_id": app_config['TOB_CONNECTION'],
            "credential_definition_id": credential_definition_id,
            "credential_values": sample_credential['attributes']
        }
        response = requests.post(agent_admin_url+'/credential_exchange/send', json.dumps(cred_offer))
        response.raise_for_status()
        cred_data = response.json()
        print("Sent offer", cred_data['credential_exchange_id'], cred_data['connection_id'], cred_data['state'], cred_data['credential_definition_id'])
        time.sleep(5)

    pass


TOPIC_CONNECTIONS = "connections"
TOPIC_CREDENTIALS = "credentials"
TOPIC_PRESENTATIONS = "presentations"
TOPIC_GET_ACTIVE_MENU = "get-active-menu"
TOPIC_PERFORM_MENU_ACTION = "perform-menu-action"
TOPIC_ISSUER_REGISTRATION = "issuer_registration"


def handle_connections(state, message):
    # TODO auto-accept?
    print("handle_connections()", state)
    return Response(state)

def handle_credentials(state, message):
    # TODO auto-respond to proof requests
    print("handle_credentials()", state)
    return Response(some_data)

def handle_presentations(state, message):
    # TODO auto-respond to proof requests
    print("handle_presentations()", state)
    return Response(some_data)

def handle_get_active_menu(message):
    # TODO add/update issuer info?
    print("handle_get_active_menu()", message)
    return Response("")

def handle_perform_menu_action(message):
    # TODO add/update issuer info?
    print("handle_perform_menu_action()", message)
    return Response("")

def handle_register_issuer(message):
    # TODO add/update issuer info?
    print("handle_register_issuer()", message)
    return Response("")

