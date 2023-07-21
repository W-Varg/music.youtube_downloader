#!/bin/bash

# Replace "app" with the name of the Python module where your Flask app is defined
gunicorn app:app -b 127.0.0.1:5000 --log-level=error
