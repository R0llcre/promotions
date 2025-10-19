######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Module: error_handlers
"""

from flask import jsonify, make_response
from flask import current_app as app  # Import Flask application
from werkzeug.exceptions import MethodNotAllowed
from service.models import DataValidationError, DatabaseError
from service.common import status


# ---------- unified response builder ----------
def _error(status_code: int, title: str, message: str):
    """Return a uniform JSON error payload."""
    return jsonify(status=status_code, error=title, message=message), status_code


######################################################################
# Error Handlers
######################################################################
@app.errorhandler(DataValidationError)
def request_validation_error(error):
    """Handles data validation errors with 400_BAD_REQUEST"""
    app.logger.warning("Bad Request: %s", error)
    return _error(status.HTTP_400_BAD_REQUEST, "Bad Request", str(error))


@app.errorhandler(status.HTTP_400_BAD_REQUEST)
def bad_request(error):
    """Handles bad requests with 400_BAD_REQUEST"""
    app.logger.warning("Bad Request: %s", error)
    return _error(status.HTTP_400_BAD_REQUEST, "Bad Request", str(error))


@app.errorhandler(status.HTTP_404_NOT_FOUND)
def not_found(error):
    """Handles resources not found with 404_NOT_FOUND"""
    app.logger.warning("Not Found: %s", error)
    return _error(status.HTTP_404_NOT_FOUND, "Not Found", str(error))


@app.errorhandler(status.HTTP_405_METHOD_NOT_ALLOWED)
def method_not_allowed(error):
    """Handles unsupported HTTP methods with 405_METHOD_NOT_ALLOWED"""
    app.logger.warning("Method Not Allowed: %s", error)
    resp = make_response(
        jsonify(
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            error="Method Not Allowed",
            message=str(error),
        ),
        status.HTTP_405_METHOD_NOT_ALLOWED,
    )
    # Advertise allowed methods if available on Werkzeug's MethodNotAllowed
    if isinstance(error, MethodNotAllowed) and getattr(error, "valid_methods", None):
        resp.headers["Allow"] = ", ".join(error.valid_methods)
    return resp


@app.errorhandler(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
def media_type_not_supported(error):
    """Handles unsupported media requests with 415_UNSUPPORTED_MEDIA_TYPE"""
    app.logger.warning("Unsupported Media Type: %s", error)
    return _error(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "Unsupported Media Type",
        str(error),
    )


@app.errorhandler(DatabaseError)
def database_error(error):
    """Handles database errors with 500_INTERNAL_SERVER_ERROR"""
    # log details server-side; do not leak internals to clients
    app.logger.error("Database error: %s", error)
    return _error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal Server Error",
        "An unexpected error occurred.",
    )


@app.errorhandler(status.HTTP_500_INTERNAL_SERVER_ERROR)
def internal_server_error(error):
    """Handles unexpected server errors with 500_INTERNAL_SERVER_ERROR"""
    # log details server-side; do not leak internals to clients
    app.logger.error("Unhandled exception: %s", error)
    return _error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal Server Error",
        "An unexpected error occurred.",
    )
