"""For services (like gunicorn) that want an WSGI application in a top-level
varilable"""
from . import api

app = api.create_app()
