#!/bin/bash

# Docs https://docs.gunicorn.org/en/stable/settings.html#workers

export PYTHONPATH=$PYTHONPATH:$(pwd)/ai_ta_backend
exec gunicorn --workers=30 --threads=16 --worker-class=gthread ai_ta_backend.main:app --timeout 1800