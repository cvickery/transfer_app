import multiprocessing
workers = multiprocessing.cpu_count() * 2 + 1

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

  We recommend setting the number of workers to 2-4 times the number of cpu_countU cores for your
  instance plus one. You can specify this in gunicorn.conf.py as:

"""
# workers = multiprocessing.cpu_count() * 2 + 1

"""
  Trying an async model to deal with 502 errors.
  502 Errors were (probably) due to use of sqlite and should disappear with the adoption of
  postgres for the database. However, the async model should do no harm and is retained.
"""
# worker_class = 'gevent'