import os
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
bind = '0.0.0.0:5000'
# On Heroku, there were 8 cpus, each of which was trying to create a PgConnection pool.
# But hobby-basic only allows 20 connections total.
# And the port number is an environment variable
if os.getenv('HEROKU') is not None:
  workers = 2
  bind = f'0.0.0.0:{os.getenv("PORT")}'

access_log_format = '%(h)s %(t)s %(r)s %(s)s %(b)s %(f)s'

if os.getenv('DEVELOPMENT') is not None:
  accesslog = '/Users/vickery/Transfer_App/Logs/transfer-app.log'
  errorlog = '/Users/vickery/Transfer_App/Logs/transfer-app.log'
  loglevel = 'DEBUG'
  reload = True
else:
  accesslog = '-'
  errorlog = '-'
  loglevel = 'INFO'
  reload = False

"""
  App Engine terminates the HTTPS connection at the load balancer and forwards the request to your
  application. Most applications do not need to know if the request was sent over HTTPS or not, but
  applications that do need this information should configure Gunicorn to trust the App Engine proxy
  in their gunicorn.conf.py:
"""
# forwarded_allow_ips = '*'
# secure_scheme_headers = {'X-APPENGINE-HTTPS': 'on'}

"""
  Gunicorn uses workers to handle requests. By default, Gunicorn uses sync workers. This worker
  class is compatible with all web applications, but each worker can only handle one request at a
  time. By default, gunicorn only uses one of these workers. This can often cause your instances to
  be underutilized and increase latency in applications under high load.

  We recommend setting the number of workers to 2-4 times the number of cpu_count cores for your
  instance plus one. You can specify this in gunicorn.conf.py as:

"""
# workers = multiprocessing.cpu_count() * 2 + 1
