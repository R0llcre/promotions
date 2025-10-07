"""
Package: service
Create and configure the Flask app, logging, and database
"""

import sys
from flask import Flask
from service import config
from service.common import log_handlers

# -----------------------------------------------------------------------------
# Create ONE global Flask app so `from service import app` 能拿到注册好路由的实例
# 也同时提供 create_app() 给测试/外部调用（返回同一个 app）
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(config)

# 初始化数据库插件
from service.models import db  # pylint: disable=wrong-import-position
db.init_app(app)

with app.app_context():
    # 必须在 app 创建后再导入这些模块，确保 @app.route 绑定到当前 app
    from service import routes, models  # noqa: F401  pylint: disable=unused-import, wrong-import-position
    from service.common import error_handlers, cli_commands  # noqa: F401  pylint: disable=unused-import, wrong-import-position

    try:
        db.create_all()
    except Exception as err:  # pylint: disable=broad-except
        app.logger.critical("%s: Cannot continue", err)
        sys.exit(4)

    # 配置日志
    log_handlers.init_logging(app, "gunicorn.error")

    app.logger.info(70 * "*")
    app.logger.info("  P R O M O T I O N S   S E R V I C E   I N I T  ".center(70, "*"))
    app.logger.info(70 * "*")


def create_app():
    """Factory-style accessor to the (already created) global app.

    兼容 `from service import create_app` 的测试/脚本。
    """
    return app



