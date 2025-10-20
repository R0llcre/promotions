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

# Standard library
from datetime import date, timedelta

# Third-party
from flask import abort, current_app as app, jsonify, request, url_for
from sqlalchemy import or_

# First-party
from service.common import status  # HTTP status codes
from service.models import DataValidationError, Promotion


def _parse_bool_strict(value: str):
    """
    Strictly parse query-string boolean.
    Accepted (case-insensitive, trimmed):
      True:  'true', '1', 'yes'
      False: 'false', '0', 'no'
    Others: return None (caller should raise 400)
    """
    v = str(value).strip().lower()
    if v in {"true", "1", "yes"}:
        return True
    if v in {"false", "0", "no"}:
        return False
    return None


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
            paths={
                "promotions": "/promotions",
            },
        ),
        status.HTTP_200_OK,
    )


######################################################################
# LIST Promotions with optional filters

# Supported query params:
# ?id=<int>              -> single record as [ ... ] or []
# ?active=<bool>         -> true =>  active today (inclusive)
#                           false => inactive today (start_date > today OR end_date < today)
#                           Accepted: true/false/1/0/yes/no (case-insensitive)
#                           Invalid => 400
# ?name=<str>            -> exact match list
# ?product_id=<int>      -> exact match list
# ?promotion_type=<str>  -> exact match list
# Priority: id > active > name > product_id > promotion_type > all
######################################################################
@app.route("/promotions", methods=["GET"])
def list_promotions():
    """
    List Promotions
    - Without query: return all promotions
    - With filter: return exact matches
    """
    app.logger.info("Request to list Promotions")

    promotion_id = request.args.get("id")
    active_raw = request.args.get("active")
    name = request.args.get("name")
    product_id = request.args.get("product_id")
    ptype = request.args.get("promotion_type")

    # 1) by id
    if promotion_id:
        app.logger.info("Filtering by id=%s", promotion_id)
        p = Promotion.find(promotion_id)
        promotions = [p] if p else []

    # 2) by active (strict)
    elif active_raw is not None:
        active = _parse_bool_strict(active_raw)
        if active is None:
            abort(
                status.HTTP_400_BAD_REQUEST,
                (
                    "Invalid value for query parameter 'active'. "
                    "Accepted: true, false, 1, 0, yes, no (case-insensitive). "
                    f"Received: {active_raw!r}"
                ),
            )

        today = date.today()
        if active is True:
            app.logger.info("Filtering by active promotions (inclusive)")
            promotions = Promotion.find_active()  # start_date <= today <= end_date  (model)  # noqa
        else:
            app.logger.info("Filtering by inactive promotions (not active today)")
            promotions = list(
                Promotion.query.filter(
                    or_(Promotion.start_date > today, Promotion.end_date < today)
                ).all()
            )

    # 3+) the rest
    elif name:
        app.logger.info("Filtering by name=%s", name)
        promotions = Promotion.find_by_name(name.strip())
    elif product_id:
        app.logger.info("Filtering by product_id=%s", product_id)
        promotions = Promotion.find_by_product_id(product_id.strip())
    elif ptype:
        app.logger.info("Filtering by promotion_type=%s", ptype)
        promotions = Promotion.find_by_promotion_type(ptype.strip())
    else:
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
        # Optional strictness: if client provides id and it disagrees with path
        if "id" in data and str(data["id"]) != str(promotion_id):
            abort(status.HTTP_400_BAD_REQUEST, "ID in body must match resource path")
        promotion.deserialize(data)
        promotion.id = promotion_id  # ensure path id takes precedence
        promotion.update()
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))

    return jsonify(promotion.serialize()), status.HTTP_200_OK


######################################################################
# DEACTIVATE a Promotion (action)
######################################################################
@app.route("/promotions/<int:promotion_id>/deactivate", methods=["PUT"])
def deactivate_promotion(promotion_id: int):
    """
    Action: Immediately deactivate a promotion by setting its end_date to yesterday (today - 1 day).
    This ensures the promotion is NOT considered active today under an inclusive active-window check,
    and preserves history without deleting the record.
    """
    app.logger.info("Request to deactivate Promotion with id [%s]", promotion_id)
    promotion = Promotion.find(promotion_id)
    if not promotion:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Promotion with id '{promotion_id}' was not found.",
        )

    try:
        yesterday = date.today() - timedelta(days=1)
        # never extend a promotion that already ended earlier than yesterday
        promotion.end_date = min(promotion.end_date, yesterday)
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
    - If the promotion doesn't exist, return 404
    - If exists, delete and return 204
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
    """Checks that the media type is correct (tolerates charset etc.)"""
    # Werkzeug exposes parsed mimetype; if header missing, this is None
    if request.mimetype != content_type:
        got = request.content_type or "none"
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}; received {got}",
        )


######################################################################
# Endpoint: /health (K8s liveness/readiness)
######################################################################
@app.route("/health", methods=["GET"])
def health():
    """
    K8s health check endpoint
    Returns:
        JSON: {"status": "OK"} with HTTP 200
    Notes:
        - Keep this endpoint lightweight and independent of external deps (e.g., DB)
          so that liveness/readiness probes are stable .
    """
    app.logger.info("Health check requested")
    return jsonify(status="OK"), status.HTTP_200_OK
