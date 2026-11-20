#!/bin/bash

# Replace "app" with the name of the Python module where your Flask app is defined
# gunicorn app:app -b 172.27.38.53:6001 --log-level=error

gunicorn app:app -b 127.0.0.1:6001 --log-level=error
