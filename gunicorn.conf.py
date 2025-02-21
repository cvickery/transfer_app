"""Configuration module for gunicorn."""
import multiprocessing
import os

port_num = 5000 if os.getenv('TREX_PORT') is None else int(os.getenv('TREX_PORT'))
print(f'Using port {port_num}')
workers = multiprocessing.cpu_count()   # * 2 + 1
bind = f'127.0.0.1:{port_num}'
timeout = 120

accesslog = './Logs/transfer_access.log'
errorlog = './Logs/transfer_error.log'
loglevel = 'info'
access_log_format = '%(h)s %({x-forwarded-for}i)s %(t)s %(r)s %(s)s %(b)s %(f)s'

reload = False

"""
  App Engine terminates the HTTPS connection at the load balancer and forwards the request to your
  application. Most applications do not need to know if the request was sent over HTTPS or not, but
  applications that do need this information should configure Gunicorn to trust the App Engine proxy
  in their gunicorn.conf.py:
"""
# forwarded_allow_ips = '*'
# secure_scheme_headers = {'X-APPENGINE-HTTPS': 'on'}
