import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

# 環境判定
IS_PRODUCTION = os.getenv("FLASK_ENV") == "production"

if IS_PRODUCTION:
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# SQLAlchemy initialization
db = SQLAlchemy(model_class=Base)

class Config:
    SECRET_KEY = os.environ.get("SESSION_SECRET")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    FITBIT_CLIENT_ID = os.environ.get("FITBIT_CLIENT_ID")
    FITBIT_CLIENT_SECRET = os.environ.get("FITBIT_CLIENT_SECRET")

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///development.db"
    )
    FITBIT_REDIRECT_URI = os.environ.get(
        "FITBIT_REDIRECT_URI", "http://localhost:5000/callback"
    )

class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    FITBIT_REDIRECT_URI = os.environ.get(
        "FITBIT_REDIRECT_URI", "https://fitbit.demagenai.com/callback"
    )
    PREFERRED_URL_SCHEME = "https"

CONFIG_CLASS = ProductionConfig if IS_PRODUCTION else DevelopmentConfig


def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.config.from_object(CONFIG_CLASS)
    db.init_app(app)

    if not initialize_app(app):
        app.logger.error("Application failed to initialize properly")

    return app


def initialize_app(app):
    """Initialize models and routes safely"""
    try:
        with app.app_context():
            import models

            db.engine.connect()
            app.logger.info("Database connection successful")

            db.create_all()
            app.logger.info("Database tables created successfully")

        import routes
        app.logger.info("Routes imported successfully")

        return True
    except Exception as e:
        app.logger.error(f"Application initialization failed: {e}")
        import traceback

        app.logger.error(traceback.format_exc())
        return False


app = create_app()


@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal Server Error: {error}")
    try:
        db.session.rollback()
    except Exception:
        pass

    if IS_PRODUCTION:
        return (
            """
        <html>
            <head><title>システムエラー</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>システムエラー</h1>
                <p>申し訳ございません。一時的なエラーが発生しました。</p>
                <p>しばらく経ってからもう一度お試しください。</p>
                <a href="/" style="color: #007bff;">ホームに戻る</a>
            </body>
        </html>
        """,
            500,
        )
    else:
        return f"Internal Server Error: {error}", 500


@app.errorhandler(404)
def not_found_error(error):
    return (
        """
    <html>
        <head><title>ページが見つかりません</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>404 - ページが見つかりません</h1>
            <p>お探しのページは存在しません。</p>
            <a href="/" style="color: #007bff;">ホームに戻る</a>
        </body>
    </html>
    """,
        404,
    )


@app.route("/health")
def basic_health():
    """Basic health check"""
    return {"status": "ok", "app": "running"}, 200
