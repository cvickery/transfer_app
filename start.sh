#! /usr/local/bin/bash
#
# Start the transfer-app
gunicorn  --bind 0.0.0.0:5000 \
          --config gunicorn.conf.py \
          --access-logfile ~/Logs/transfer-app.log \
          --log-file - \
          --log-level info \
          main:app
