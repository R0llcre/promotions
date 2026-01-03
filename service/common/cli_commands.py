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
Flask CLI Command Extensions
"""
from datetime import date, timedelta
from flask import current_app as app  # Import Flask application
from service.models import db, Promotion


######################################################################
# Command to force tables to be rebuilt
# Usage:
#   flask db-create
######################################################################
@app.cli.command("db-create")
def db_create():
    """
    Recreates a local database. You probably should not use this on
    production. ;-)
    """
    db.drop_all()
    db.create_all()
    db.session.commit()


######################################################################
# Command to load sample data
# Usage:
#   flask load-data
######################################################################
@app.cli.command("load-data")
def load_data():
    """
    Loads sample promotions data into the database for testing.
    Creates various types of promotions: PERCENT, DISCOUNT, and BOGO.
    """
    app.logger.info("Loading sample data...")

    # Sample data for different promotion types
    today = date.today()
    promotions = [
        # PERCENT type promotions
        {
            "name": "Summer Sale 20% Off",
            "promotion_type": "PERCENT",
            "value": 20,
            "product_id": 101,
            "img_url": "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat()
        },
        {
            "name": "Black Friday 50% Discount",
            "promotion_type": "PERCENT",
            "value": 50,
            "product_id": 102,
            "img_url": "https://images.unsplash.com/photo-1607082349566-187342175e2f",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat()
        },
        {
            "name": "Winter Clearance 30% Off",
            "promotion_type": "PERCENT",
            "value": 30,
            "product_id": 103,
            "img_url": "https://images.unsplash.com/photo-1483985988355-763728e1935b",
            "start_date": (today - timedelta(days=10)).isoformat(),
            "end_date": (today + timedelta(days=20)).isoformat()
        },
        # DISCOUNT type promotions
        {
            "name": "Holiday Special $10 Off",
            "promotion_type": "DISCOUNT",
            "value": 10,
            "product_id": 201,
            "img_url": "https://images.unsplash.com/photo-1513885535751-8b9238bd345a",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=15)).isoformat()
        },
        {
            "name": "New Customer $25 Discount",
            "promotion_type": "DISCOUNT",
            "value": 25,
            "product_id": 202,
            "img_url": "https://images.unsplash.com/photo-1441986300917-64674bd600d8",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=60)).isoformat()
        },
        {
            "name": "Flash Sale $5 Off",
            "promotion_type": "DISCOUNT",
            "value": 5,
            "product_id": 203,
            "img_url": "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=3)).isoformat()
        },
        # BOGO type promotions
        {
            "name": "Buy One Get One Free",
            "promotion_type": "BOGO",
            "value": 1,
            "product_id": 301,
            "img_url": "https://images.unsplash.com/photo-1567401893414-76b7b1e5a7a5",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=14)).isoformat()
        },
        {
            "name": "BOGO 50% Off Second Item",
            "promotion_type": "BOGO",
            "value": 50,
            "product_id": 302,
            "img_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=21)).isoformat()
        },
        {
            "name": "Weekend BOGO Special",
            "promotion_type": "BOGO",
            "value": 1,
            "product_id": 303,
            "img_url": "https://images.unsplash.com/photo-1491553895911-0055eca6402d",
            "start_date": (today - timedelta(days=5)).isoformat(),
            "end_date": (today + timedelta(days=2)).isoformat()
        },
        # Some expired promotions for testing inactive filter
        {
            "name": "Expired Spring Sale",
            "promotion_type": "PERCENT",
            "value": 25,
            "product_id": 401,
            "img_url": "https://images.unsplash.com/photo-1445205170230-053b83016050",
            "start_date": (today - timedelta(days=60)).isoformat(),
            "end_date": (today - timedelta(days=30)).isoformat()
        },
        {
            "name": "Past Holiday Discount",
            "promotion_type": "DISCOUNT",
            "value": 15,
            "product_id": 402,
            "img_url": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f",
            "start_date": (today - timedelta(days=45)).isoformat(),
            "end_date": (today - timedelta(days=15)).isoformat()
        },
    ]

    created_count = 0
    for promo_data in promotions:
        promotion = Promotion()
        promotion.deserialize(promo_data)
        promotion.create()
        created_count += 1
        app.logger.info("Created: %s (%s)", promotion.name, promotion.promotion_type)

    app.logger.info("Loaded %d promotions into the database", created_count)
    print(f"✓ Successfully loaded {created_count} sample promotions")
