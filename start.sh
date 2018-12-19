#! /usr/local/bin/bash
#
# Start the transfer-app
if [[ -r gunicorn.pid ]]
then kill `cat gunicorn.pid`
     prefix='re'
fi
rm -f gunicorn.pid

gunicorn  --bind 0.0.0.0:5000 \
          --config gunicorn.conf.py \
          --access-logfile ~/Logs/transfer-app-access.log \
          --error-logfile ~/Logs/transfer-app-error.log \
          --log-level info \
          main:app &
echo $! > gunicorn.pid
echo gunicorn ${prefix}started with pid $!
