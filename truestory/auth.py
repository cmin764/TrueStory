"""Tackles secrets, authentication and authorization."""


import hashlib
import hmac
import re

from flask import request

from truestory import datautil, misc, settings


CAPTCHA_URL = "https://www.google.com/recaptcha/api/siteverify"
RE_HOST = re.compile(r"localhost|truestory", re.IGNORECASE)


def get_secret(name):
    return datautil.get_string(f"secrets/{name}")


def compute_token(mail):
    from truestory import app  # circular dependency
    return hmac.new(
        app.secret_key, msg=mail.encode(settings.ENCODING), digestmod=hashlib.md5
    ).hexdigest()


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
    session = misc.RequestsSession()
    resp = session.post(CAPTCHA_URL, data=data)
    resp.raise_for_status()
    result = resp.json()
    errors = result.get("error-codes")
    if errors:
        raise ValueError(", ".join(errors))
    assert RE_HOST.search(result["hostname"])
    return result["success"]
