#!/usr/bin/env python3
"""WSGI entry point for Gunicorn"""
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()

if not app.debug:
    import logging
    logging.basicConfig(level=logging.INFO)
