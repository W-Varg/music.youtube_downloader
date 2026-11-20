#!/bin/bash

# Replace "app" with the name of the Python module where your Flask app is defined
gunicorn app:app -b 172.27.39.12:6000 --log-level=error
