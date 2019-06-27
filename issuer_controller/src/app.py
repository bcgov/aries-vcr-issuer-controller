#!/usr/bin/env python
from flask import Flask, jsonify, abort, make_response, request
from flask_script import Manager, Server

import requests
import json
import os
import time


def custom_call():
    # read configuration files
    alias = 'Demo issuer'
    seed = '00000000000000000000000000000001'
    schema_name = 'ian-permit.ian-ville'
    schema_version = '1.0.0'
    schema_attrs = ["permit_issued_date", "permit_type", "permit_status", "effective_date", "corp_num"]
    sample_credential = {
        "permit_issued_date": "2018-01-01", 
        "permit_type": "ABC", 
        "permit_status": "OK", 
        "effective_date": "2019-01-01", 
        "corp_num": "ABC12345"
    }

    agent_admin_url = os.environ.get('AGENT_ADMIN_URL')
    if not agent_admin_url:
        raise RuntimeError("Error AGENT_ADMIN_URL is not specified, can't connect to Agent.")

    # ensure DID is registered
    ledger_url = os.environ.get('LEDGER_URL')
    if ledger_url:
        # register DID
        response = requests.post(ledger_url+'/register', json.dumps({"alias": alias, "seed": seed, "role": "TRUST_ANCHOR"}))
        response.raise_for_status()
        did = response.json()
        print("Registered did", did)
        time.sleep(3)

    # register our schema(s) and credential definition(s)
    schema_request = {"schema_name": schema_name, "schema_version": schema_version, "attributes": schema_attrs}
    response = requests.post(agent_admin_url+'/schemas', json.dumps(schema_request))
    response.raise_for_status()
    schema_id = response.json()
    print("Registered schema", schema_id)
    time.sleep(3)

    cred_def_request = {"schema_id": schema_id['schema_id']}
    response = requests.post(agent_admin_url+'/credential-definitions', json.dumps(cred_def_request))
    response.raise_for_status()
    credential_definition_id = response.json()
    print("Registered credential definition", credential_definition_id)
    time.sleep(3)

    # check if we have a TOB connection
    response = requests.get(agent_admin_url+'/connections')
    response.raise_for_status()
    connections = response.json()['results']
    tob_connection = None
    for connection in connections:
        # check for TOB connection
        if connection['their_label'] == 'tob-agent':
            tob_connection = connection

    if not tob_connection:
        # if no tob connection then establish one
        tob_agent_admin_url = os.environ.get('TOB_AGENT_ADMIN_URL')
        if not tob_agent_admin_url:
            raise RuntimeError("Error TOB_AGENT_ADMIN_URL is not specified, can't establish a TOB connection.")

        response = requests.post(tob_agent_admin_url+'/connections/create-invitation')
        response.raise_for_status()
        invitation = response.json()

        response = requests.post(agent_admin_url+'/connections/receive-invitation', json.dumps(invitation['invitation']))
        response.raise_for_status()
        tob_connection = response.json()

        print("Established tob connection", tob_connection)
        time.sleep(3)

    # register ourselves (issuer, schema(s), cred def(s)) with TOB
    tob_connection_id = tob_connection['connection_id']
    issuer_request = {
        "connection_id": tob_connection_id,
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
                "did": did['did'],
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
    print("Registered issuer", issuer_data)

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

class CustomServer(Server):
    def __call__(self, app, *args, **kwargs):
        custom_call()
        #Hint: Here you could manipulate app
        return Server.__call__(self, app, *args, **kwargs)

app = Flask(__name__)
manager = Manager(app)

# Remeber to add the command to your Manager instance
manager.add_command('runserver', CustomServer())

tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/todo/api/v1.0/tasks', methods=['GET'])
def get_tasks():
    return jsonify({'tasks': tasks})

@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    return jsonify({'task': task[0]})

@app.route('/todo/api/v1.0/tasks', methods=['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        abort(400)
    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    tasks.append(task)
    return jsonify({'task': task}), 201

@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    if not request.json:
        abort(400)
    if 'title' in request.json and type(request.json['title']) != unicode:
        abort(400)
    if 'description' in request.json and type(request.json['description']) is not unicode:
        abort(400)
    if 'done' in request.json and type(request.json['done']) is not bool:
        abort(400)
    task[0]['title'] = request.json.get('title', task[0]['title'])
    task[0]['description'] = request.json.get('description', task[0]['description'])
    task[0]['done'] = request.json.get('done', task[0]['done'])
    return jsonify({'task': task[0]})

@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    tasks.remove(task[0])
    return jsonify({'result': True})

if __name__ == '__main__':
    manager.run()
