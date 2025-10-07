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
Promotion Service

This service implements a REST API that allows you to
Create, Read, Update, Delete, and List Promotions
"""

from flask import jsonify, request, url_for, abort
from flask import current_app as app
from service.models import Promotion
from service.common import status  # HTTP status codes


######################################################################
# GET INDEX
######################################################################
@app.route("/")
def index():
    """Root URL response"""
    return jsonify(
        name="Promotions Service",
        version="1.0.0",
        description="RESTful service for managing promotions",
        paths={
            # 测试期望的 key 叫 "promotions"
            "promotions": "/promotions"
        },
    ), status.HTTP_200_OK


######################################################################
# LIST ALL PROMOTIONS
######################################################################
@app.route("/promotions", methods=["GET"])
def list_promotions():
    """Returns a list of all Promotions"""
    app.logger.info("Request for promotion list")
    promotions = Promotion.all()
    results = [promo.serialize() for promo in promotions]
    app.logger.info("Returning %d promotions", len(results))
    return jsonify(results), status.HTTP_200_OK


######################################################################
# READ A PROMOTION
######################################################################
@app.route("/promotions/<int:promotion_id>", methods=["GET"])
def get_promotions(promotion_id):
    """Retrieve a single Promotion by ID"""
    app.logger.info("Request for promotion id [%s]", promotion_id)
    promo = Promotion.find(promotion_id)
    if not promo:
        app.logger.warning("Promotion id [%s] not found", promotion_id)
        abort(status.HTTP_404_NOT_FOUND, description=f"Promotion with id={promotion_id} not found")
    return jsonify(promo.serialize()), status.HTTP_200_OK


######################################################################
# CREATE A NEW PROMOTION
######################################################################
@app.route("/promotions", methods=["POST"])
def create_promotions():
    """Create a Promotion"""
    app.logger.info("Request to create a Promotion")
    check_content_type("application/json")

    data = request.get_json()
    app.logger.info("Processing: %s", data)

    promotion = Promotion()
    promotion.deserialize(data)
    promotion.create()
    app.logger.info("Promotion with id [%s] created", promotion.id)

    location_url = url_for("get_promotions", promotion_id=promotion.id, _external=True)
    return jsonify(promotion.serialize()), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# UPDATE AN EXISTING PROMOTION
######################################################################
@app.route("/promotions/<int:promotion_id>", methods=["PUT"])
def update_promotions(promotion_id):
    """Update an existing Promotion"""
    app.logger.info("Request to update promotion id [%s]", promotion_id)
    check_content_type("application/json")

    promo = Promotion.find(promotion_id)
    if not promo:
        abort(status.HTTP_404_NOT_FOUND, description=f"Promotion with id={promotion_id} not found")

    data = request.get_json()
    app.logger.info("Processing update: %s", data)

    # 防止请求体里带 id 覆盖
    if isinstance(data, dict):
        data.pop("id", None)

    promo.deserialize(data)
    promo.id = promotion_id
    # 适配不同模型实现：有 update() 用 update()，否则用 save()
    if hasattr(promo, "update"):
        promo.update()
    elif hasattr(promo, "save"):
        promo.save()

    app.logger.info("Promotion id [%s] updated", promo.id)
    return jsonify(promo.serialize()), status.HTTP_200_OK


######################################################################
# DELETE A PROMOTION
######################################################################
@app.route("/promotions/<int:promotion_id>", methods=["DELETE"])
def delete_promotions(promotion_id):
    """Delete a Promotion by ID"""
    app.logger.info("Request to delete promotion id [%s]", promotion_id)
    promo = Promotion.find(promotion_id)
    if not promo:
        app.logger.warning("Promotion id [%s] not found", promotion_id)
        abort(status.HTTP_404_NOT_FOUND, description=f"Promotion with id={promotion_id} not found")

    promo.delete()
    app.logger.info("Promotion id [%s] deleted", promotion_id)
    return "", status.HTTP_204_NO_CONTENT


######################################################################
# U T I L I T Y   F U N C T I O N S
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Content-Type must be {content_type}")

    if request.headers["Content-Type"] != content_type:
        app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
        abort(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Content-Type must be {content_type}")
