######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
Promotions Service

This service implements a REST API that allows you to Create, Read, Update,
Delete and List Promotions
"""

from flask import jsonify, request, url_for, abort
from flask import current_app as app
from service.models import Promotion, DataValidationError
from service.common import status  # HTTP status codes


######################################################################
# Root endpoint
######################################################################
@app.route("/", methods=["GET"])
def index():
    """Root URL response"""
    return (
        jsonify(
            name="Promotions Service",
            version="1.0.0",
            description="RESTful service for managing promotions",
            paths={"promotions": "/promotions"},
        ),
        status.HTTP_200_OK,
    )


######################################################################
# LIST Promotions
######################################################################
@app.route("/promotions", methods=["GET"])
def list_promotions():
    """
    List Promotions
    Returns all promotions
    """
    app.logger.info("Request to list Promotions")
    promotions = Promotion.all()
    results = [p.serialize() for p in promotions]
    return jsonify(results), status.HTTP_200_OK


######################################################################
# READ a Promotion
######################################################################
@app.route("/promotions/<int:promotion_id>", methods=["GET"])
def get_promotions(promotion_id: int):
    """
    Get a Promotion by id
    """
    app.logger.info("Request to get Promotion with id [%s]", promotion_id)
    promotion = Promotion.find(promotion_id)
    if not promotion:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Promotion with id '{promotion_id}' was not found.",
        )
    return jsonify(promotion.serialize()), status.HTTP_200_OK


######################################################################
# CREATE a Promotion
######################################################################
@app.route("/promotions", methods=["POST"])
def create_promotions():
    """
    Create a Promotion
    """
    app.logger.info("Request to Create a Promotion")
    check_content_type("application/json")

    promotion = Promotion()
    try:
        data = request.get_json()
        app.logger.info("Processing: %s", data)
        promotion.deserialize(data)
        promotion.create()
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    location_url = url_for("get_promotions", promotion_id=promotion.id, _external=True)
    return (
        jsonify(promotion.serialize()),
        status.HTTP_201_CREATED,
        {"Location": location_url},
    )


######################################################################
# UPDATE a Promotion
######################################################################
@app.route("/promotions/<int:promotion_id>", methods=["PUT"])
def update_promotions(promotion_id: int):
    """
    Update a Promotion
    Replaces fields of a promotion with payload values
    """
    app.logger.info("Request to update Promotion with id [%s]", promotion_id)
    check_content_type("application/json")

    promotion = Promotion.find(promotion_id)
    if not promotion:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Promotion with id '{promotion_id}' was not found.",
        )

    try:
        data = request.get_json()
        app.logger.info("Processing: %s", data)
        promotion.deserialize(data)
        promotion.id = promotion_id  # ensure path id takes precedence
        promotion.update()
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    return jsonify(promotion.serialize()), status.HTTP_200_OK


######################################################################
# DELETE a Promotion
######################################################################
@app.route("/promotions/<int:promotion_id>", methods=["DELETE"])
def delete_promotions(promotion_id: int):
    """
    Delete a Promotion by id
    """
    app.logger.info("Request to delete Promotion with id [%s]", promotion_id)
    promotion = Promotion.find(promotion_id)
    if not promotion:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Promotion with id '{promotion_id}' was not found.",
        )

    promotion.delete()
    return "", status.HTTP_204_NO_CONTENT


######################################################################
# Utility: Content-Type guard
######################################################################
def check_content_type(content_type: str):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )
