#
# Copyright 2017-2018 Government of Canada
# Public Services and Procurement Canada - buyandsell.gc.ca
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Connection handling specific to using the OrgBook as a holder/prover
"""

import base64
import logging
import pathlib

LOGGER = logging.getLogger(__name__)

CRED_TYPE_PARAMETERS = (
    "cardinality_fields",
    "category_labels",
    "claim_descriptions",
    "claim_labels",
    "credential",
    "details",
    "mapping",
    "topic",
    "visible_fields",
)


def encode_logo_image(config: dict, path_root: str) -> str:
    """
    Encode logo image as base64 for transmission
    """
    if config.get("logo_b64"):
        return config["logo_b64"]
    elif config.get("logo_path"):
        path = pathlib.Path(path_root, config["logo_path"])
        if path.is_file():
            content = path.read_bytes()
            if content:
                return base64.b64encode(content).decode("ascii")
        else:
            LOGGER.warning("No file found at logo path: %s", path)
    return None


def extract_translated(config: dict, field: str, defval=None, deflang: str = "en"):
    ret = {deflang: defval}
    if config:
        pfx = field + "_"
        for k, v in config.items():
            if k == field:
                ret[deflang] = v
            elif k.startswith(pfx):
                lang = k[len(pfx) :]
                if lang:
                    ret[lang] = v
    return ret


def assemble_issuer_spec(config: dict) -> dict:
    """
    Create the issuer JSON definition which will be submitted to the OrgBook
    """

    config_root = config.get("config_root")
    deflang = "en"

    details = config.get("details", {})

    abbrevs = extract_translated(details, "abbreviation", "", deflang)
    labels = extract_translated(details, "label", "", deflang)
    urls = extract_translated(details, "url", "", deflang)

    spec = {
        "name": config.get("name"),
        # "name": labels[deflang] or config.get("email"),
        "did": config.get("did"),
        "email": config.get("email"),
        "logo_b64": encode_logo_image(details, config_root),
        "abbreviation": abbrevs[deflang],
        "url": urls[deflang],
        "endpoint": config.get("endpoint"),
    }
    for k, v in abbrevs.items():
        spec["abbreviation_{}".format(k)] = v
    for k, v in labels.items():
        spec["label_{}".format(k)] = v
    for k, v in urls.items():
        spec["url_{}".format(k)] = v

    return spec


def assemble_credential_type_spec(config: dict) -> dict:
    """
    Create the issuer JSON definition which will be submitted to the OrgBook
    """

    config_root = config.get("config_root")
    deflang = "en"

    schema = config["schema"]
    if not config.get("topic"):
        raise RuntimeError("Missing 'topic' for credential type")

    if not config.get("issuer_url"):
        raise RuntimeError("Missing 'issuer_url' for credential type")

    labels = extract_translated(config, "label", config.get("schema_name"), deflang)
    urls = extract_translated(config, "url", config.get("issuer_url"), deflang)
    logo_b64 = encode_logo_image(config, config_root)

    ctype = {
        "schema": config.get("schema_name"),
        "version": config.get("schema_version"),
        "credential_def_id": config.get("credential_def_id"),
        "name": labels[deflang],
        "endpoint": urls[deflang],
        "topic": config["topic"],
        "logo_b64": logo_b64,
    }
    for k in labels:
        ctype["label_{}".format(k)] = labels[k]
    for k in urls:
        ctype["endpoint_{}".format(k)] = urls[k]
    for k in CRED_TYPE_PARAMETERS:
        if k != "details" and k in config and k not in ctype:
            ctype[k] = config[k]

    return ctype
