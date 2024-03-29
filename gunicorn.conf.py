"""Configuration module for gunicorn."""
import multiprocessing
import os
import socket


test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port_num = 5000 if os.getenv('TREX_PORT') is None else int(os.getenv('TREX_PORT'))

while (test_socket.connect_ex(('0.0.0.0', port_num))) == 0:
  port_num += 1
test_socket.close()
print(f'Using port {port_num}')
workers = multiprocessing.cpu_count() * 2 + 1
bind = f'0.0.0.0:{port_num}'
timeout = 120

accesslog = './Logs/transfer_access.log'
errorlog = './Logs/transfer_error.log'
loglevel = 'info'
access_log_format = '%(h)s %({x-forwarded-for}i)s %(t)s %(r)s %(s)s %(b)s %(f)s'

reload = True

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
