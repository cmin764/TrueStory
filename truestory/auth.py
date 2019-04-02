"""Tackles authentication and authorization."""


import hmac
import pkg_resources
import re

import requests
from flask import request

from truestory import app, settings


CAPTCHA_URL = "https://www.google.com/recaptcha/api/siteverify"

RE_HOST = re.compile(r"localhost|truestory", re.IGNORECASE)


def get_secret(name):
    content = pkg_resources.resource_string("truestory", f"secrets/{name}")
    return content.decode(settings.ENCODING).strip()


def compute_token(mail):
    return hmac.new(app.secret_key, mail.encode(settings.ENCODING)).hexdigest()


def authorize_with_token(token):
    mails = get_secret("auth_mails").splitlines()
    tokens = map(compute_token, mails)
    return token in tokens


def validate_captcha(response):
    data = {
        "secret": get_secret("captcha_key"),
        "response": response,
        "remoteip": request.remote_addr,
    }
    resp = requests.post(CAPTCHA_URL, data=data)
    resp.raise_for_status()
    result = resp.json()
    errors = result.get("error-codes")
    if errors:
        raise ValueError(", ".join(errors))
    assert RE_HOST.search(result["hostname"])
    return result["success"]
