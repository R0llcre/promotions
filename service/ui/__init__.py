"""Admin UI blueprint for the Promotions service.

This module mounts a lightweight administrator UI at `/ui`. It is used by
Requirement 4 to drive Behavior-Driven tests *via the browser only* and does
not modify or replace the existing REST API routes.
"""

from flask import Blueprint, render_template


# Serve templates from service/templates and static assets from service/static
ui_bp = Blueprint(
    "ui",
    __name__,
    template_folder="../templates",
    static_folder="../static",
)


@ui_bp.route("/ui", methods=["GET"])
def index():
    """Admin UI entry point (skeleton page)."""
    # The title is used by tests to assert that the page renders.
    return render_template("index.html", title="Promotions Admin")
