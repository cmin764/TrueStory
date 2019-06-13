"""Base API views and functions."""


import functools

from flask_restful import Resource, abort, request

from truestory import auth


def _authenticate(func):
    """Checks for authentication token within headers."""
    check_auth = (
        lambda kind, token: kind == "Bearer" and auth.authorize_with_token(token)
    )

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        auth_parts = request.headers.get("Authorization", "").strip().split()
        if len(auth_parts) == 2 and check_auth(*auth_parts):
            return func(*args, **kwargs)
        abort(401, message="Invalid or missing token.")

    return wrapper


class BaseResource(Resource):

    """Base resource API handler."""

    URL_PREFIX = ENDPOINT = ""
    method_decorators = [_authenticate]

    @classmethod
    def get_route(cls):
        """Returns the string route for the current resource."""
        return f"{cls.URL_PREFIX}/{cls.ENDPOINT}"

    @classmethod
    def get_endpoint(cls):
        """Returns the endpoint name for the current resource."""
        return f"{cls.URL_PREFIX}_{cls.ENDPOINT}".strip("/")


class DatastoreMixin:

    """Mixin handling database serialization of entities."""

    @staticmethod
    def _get_schemas():
        raise NotImplementedError("required schemas not provided")

    @classmethod
    def _make_response(cls, which, obj, **kwargs):
        schema = cls._get_schemas()[which]
        return schema.jsonify(obj, _name=which, **kwargs)
