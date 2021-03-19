import json
import os
from functools import wraps

import requests
from flask import jsonify, request
from jose import jwt


def auth_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):

        token_result = validate_token(*args, **kwargs)
        key_result = validate_api_key(*args, **kwargs)

        if token_result is False or key_result is False:
            return jsonify({"error": "Authentication failed."})

        return f(*args, **kwargs)

    return decorator


def api_key_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):

        result = validate_api_key(*args, **kwargs)

        if result is False:
            return jsonify({"error": "No valid x-api-key header was provided"})

        return f(*args, **kwargs)

    return decorator


def validate_token(*args, **kwargs):
    token = None
    oidc_jwks_uri = os.environ.get("OIDC_JWKS_URI", None)

    if oidc_jwks_uri is not None and oidc_jwks_uri is not "":
        if "Authorization" in request.headers:
            try:
                token = request.headers["Authorization"].split()[1]
                kid = jwt.get_unverified_header(token)["kid"]
                oidc_jwks = requests.get(oidc_jwks_uri).json()
                public_key = None
                algorithms = []
                for jwk in oidc_jwks["keys"]:
                    if jwk["kid"] == kid:
                        public_key = jwk
                        algorithms = [jwk["alg"]]
                jwt.decode(
                    token,
                    public_key,
                    algorithms=algorithms,
                    options={"verify_aud": False},
                )
            except Exception as e:
                print("Error verifying bearer token: " + str(e))
                return False
        else:
            return False

    return True


def validate_api_key(*args, **kwargs):
    provided_key = None
    api_key = os.environ.get("CONTROLLER_API_KEY", None)

    if api_key is not None and api_key is not "":

        if "x-api-key" in request.headers:
            provided_key = request.headers["x-api-key"]
            if provided_key != api_key:
                return False
        else:
            return False

    return True
