"""
Package: service
Create and configure the Flask app, logging, and database
"""

import sys
from flask import Flask
from service import config
from service.common import log_handlers

# -----------------------------------------------------------------------------
# Create ONE global Flask app so that `from service import app`
# returns a fully configured instance with all routes registered.
# Also provide create_app() for tests or external scripts
# (it returns the same global app instance).
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(config)

# Initialize the database plugin
from service.models import db  # pylint: disable=wrong-import-position
db.init_app(app)

with app.app_context():
    # These modules must be imported AFTER the app is created
    # so that @app.route decorators bind to this app instance.
    from service import routes, models  # noqa: F401  pylint: disable=unused-import, wrong-import-position
    from service.common import error_handlers, cli_commands  # noqa: F401  pylint: disable=unused-import, wrong-import-position

    try:
        db.create_all()
    except Exception as err:  # pylint: disable=broad-except
        app.logger.critical("%s: Cannot continue", err)
        sys.exit(4)

    # Configure logging
    log_handlers.init_logging(app, "gunicorn.error")

    app.logger.info(70 * "*")
    app.logger.info("  P R O M O T I O N S   S E R V I C E   I N I T  ".center(70, "*"))
    app.logger.info(70 * "*")


def create_app():
    """Factory-style accessor to the (already created) global app.

    Provides compatibility for tests or scripts that import
    `from service import create_app`.
    """
    return app
