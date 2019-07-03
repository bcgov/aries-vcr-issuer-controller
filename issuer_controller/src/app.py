#!/usr/bin/env python
from flask import Flask, jsonify, abort, request, make_response
from flask_script import Manager, Server

import requests
import json
import os
import time
import yaml

import config

import issuer


# Load application settings (environment)
config_root = os.environ.get('CONFIG_ROOT', '../config')
ENV = config.load_settings(config_root=config_root)

# custom server class to inject startup initialization routing
class CustomServer(Server):
    def __call__(self, app, *args, **kwargs):
        issuer.startup_init(ENV)
        #Hint: Here you could manipulate app
        return Server.__call__(self, app, *args, **kwargs)

app = Flask(__name__)
manager = Manager(app)

# Remeber to add the command to your Manager instance
manager.add_command('runserver', CustomServer())


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/api/submit-credential', methods=['POST'])
def submit_credential():
    """
    Exposed method to proxy credential issuance requests.
    """
    if not request.json:
        abort(400)

    cred_input = request.json

    # construct and send the credential
    # TODO look up the cred_def_id based on the supplied schema and version
    cred_offer = {
        "connection_id": tob_connection_id,
        "credential_definition_id": credential_definition_id['credential_definition_id'],
        "credential_values": cred_input
    }
    response = requests.post(agent_admin_url+'/credential_exchange/send', json.dumps(cred_offer))
    response.raise_for_status()
    cred_data = response.json()

    # TODO wait for confirmation from the agent, which will include the wallet id of the saved credential

    return jsonify({})


@app.route('/api/agent-cb/topic/<topic>/', methods=['POST'])
def agent_callback(topic):
    """
    Main callback for aries agent.  Dispatches calls based on the supplied topic.
    """
    if not request.json:
        abort(400)

    message = request.json

    # dispatch based on the topic type
    if topic == issuer.TOPIC_CONNECTIONS:
        return issuer.handle_connections(message["state"], message)

    elif topic == issuer.TOPIC_CREDENTIALS:
        return issuer.handle_credentials(message["state"], message)

    elif topic == issuer.TOPIC_PRESENTATIONS:
        return issuer.handle_presentations(message["state"], message)

    elif topic == issuer.TOPIC_GET_ACTIVE_MENU:
        return issuer.handle_get_active_menu(message)

    elif topic == issuer.TOPIC_PERFORM_MENU_ACTION:
        return issuer.handle_perform_menu_action(message)

    elif topic == issuer.TOPIC_ISSUER_REGISTRATION:
        return issuer.handle_register_issuer(message)

    else:
        print("Callback: topic=", topic, ", message=", message)
        abort(400, {'message': 'Invalid topic: ' + topic})


if __name__ == '__main__':
    manager.run()
