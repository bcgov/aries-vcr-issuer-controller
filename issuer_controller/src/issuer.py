from flask import jsonify, abort, request, make_response, request

import requests
import json
import os
import time
import yaml


# list of cred defs per schema name/version
app_config = {}
app_config['schemas'] = {}

def startup_init(ENV):
    global app_config

    # read configuration files
    config_root = ENV.get('CONFIG_ROOT', '../config')
    with open(config_root + "/schemas.yml", 'r') as stream:
        config_schemas = yaml.safe_load(stream)
    with open(config_root + "/services.yml", 'r') as stream:
        config_services = yaml.safe_load(stream)

    #print("schemas.yml -->", json.dumps(config_schemas))
    #print("services.yml -->", json.dumps(config_services))

    # other sample data
    sample_credential = {
        "permit_issued_date": "2018-01-01", 
        "permit_type": "ABC", 
        "permit_status": "OK", 
        "effective_date": "2019-01-01", 
        "corp_num": "ABC12345"
    }

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
        print("Registered schema", schema_id)
        app_config['schemas']['SCHEMA_' + schema_name + '_' + schema_version] = schema_id['schema_id']

        cred_def_request = {"schema_id": schema_id['schema_id']}
        response = requests.post(agent_admin_url+'/credential-definitions', json.dumps(cred_def_request))
        response.raise_for_status()
        credential_definition_id = response.json()
        print("Registered credential definition", credential_definition_id)
        app_config['schemas']['CRED_DEF_' + schema_name + '_' + schema_version] = credential_definition_id['credential_definition_id']

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

    app_config['TOB_CONNECTION'] = tob_connection['connection_id']

    for issuer_name, issuer_info in config_services['issuers'].items():
        # register ourselves (issuer, schema(s), cred def(s)) with TOB
        issuer_request = {
            "connection_id": app_config['TOB_CONNECTION'],
            "issuer_registration": {
                "credential_types": [
                    {
                        "cardinality_fields": {},
                        "category_labels": {},
                        "claim_descriptions": {},
                        "claim_labels": {},
                        "credential": {
                            "effective_date": {
                                "from": "claim",
                                "input": "effective_date"
                            }
                        },
                        "credential_def_id": "4cLztgZYocjqTdAZM93t27:3:CL:7:default",
                        "description": "Permit",
                        "endpoint": "http://localhost:5001/ian-ville/ian-permit",
                        "logo_b64": "null",
                        "mapping": [
                            {
                                "fields": {
                                    "format": {
                                        "from": "value",
                                        "input": "datetime"
                                    },
                                    "type": {
                                        "from": "value",
                                        "input": "permit_issued_date"
                                    },
                                    "value": {
                                        "from": "claim",
                                        "input": "permit_issued_date"
                                    }
                                },
                                "model": "attribute"
                            },
                            {
                                "fields": {
                                    "type": {
                                        "from": "value",
                                        "input": "permit_type"
                                    },
                                    "value": {
                                        "from": "claim",
                                        "input": "permit_type"
                                    }
                                },
                                "model": "attribute"
                            },
                            {
                                "fields": {
                                    "type": {
                                        "from": "value",
                                        "input": "permit_status"
                                    },
                                    "value": {
                                        "from": "claim",
                                        "input": "permit_status"
                                    }
                                },
                                "model": "attribute"
                            },
                            {
                                "fields": {
                                    "format": {
                                        "from": "value",
                                        "input": "datetime"
                                    },
                                    "type": {
                                        "from": "value",
                                        "input": "effective_date"
                                    },
                                    "value": {
                                        "from": "claim",
                                        "input": "effective_date"
                                    }
                                },
                                "model": "attribute"
                            }
                        ],
                        "name": "tbd",
                        "schema": "ian-permit.ian-ville",
                        "topic": {
                            "source_id": {
                                "from": "claim",
                                "input": "corp_num"
                            },
                            "type": {
                                "from": "value",
                                "input": "registration"
                            }
                        },
                        "version": "1.0.0",
                        "visible_fields": []
                    }
                ],
                "issuer": {
                    "name": alias,
                    "abbreviation": alias,
                    "did": app_config['DID'],
                    "email": "info@ian-ville.ca",
                    "endpoint": "http://192.168.65.3:5001",
                    "label": alias,
                    "logo_path": "../assets/img/ian-ville-logo.jpg",
                    "url": "https://www.ian-ville.ca/ian-ville-info-page"
                }
            }
        }

        response = requests.post(agent_admin_url+'/issuer_registration/send', json.dumps(issuer_request))
        response.raise_for_status()
        issuer_data = response.json()
        print("Registered issuer", issuer_name)

    # let's send a credential!
    cred_offer = {
        "connection_id": tob_connection_id,
        "credential_definition_id": credential_definition_id['credential_definition_id'],
        "credential_values": sample_credential
    }
    response = requests.post(agent_admin_url+'/credential_exchange/send', json.dumps(cred_offer))
    response.raise_for_status()
    cred_data = response.json()
    print("Sent offer", cred_data)

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

