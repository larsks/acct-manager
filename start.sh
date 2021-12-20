#!/bin/sh
exec gunicorn -b 0.0.0.0:8080 acct_manager.wsgi:app --log-file=-
