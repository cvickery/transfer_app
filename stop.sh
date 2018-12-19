#! /usr/local/bin/bash
# Stop gunicorn
if [[ -r gunicorn.pid ]]
then
  pid=`cat gunicorn.pid`
  kill $pid
  echo killed $pid
fi
rm -f gunicorn.pid
