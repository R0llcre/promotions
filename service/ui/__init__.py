# service/ui/__init__.py
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
    """Admin UI entry point (skeleton)"""
    # The title is used by the test to assert the page content.
    return render_template("index.html", title="Promotions Admin")
