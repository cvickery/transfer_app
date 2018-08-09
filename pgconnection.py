import psycopg2
from psycopg2.extras import NamedTupleCursor

import os
import re
import socket


class pgconnection:
  """ Wrappers for psycopg2 connect() and cursor().
      The connection will be to:
        * the local db named cuny_courses if running on GAE
        * the GAE db named cuny_courses if running on a development machine with pgproxy running
        * the local testing db named cuny_courses if running on a development machine with pgproxy
          not running.

      The cursor will use the NamedTupleCursor cursor_factory unless overridden. It includes shims
      for operational connection functions (commit() and close()).
  """
  def __init__(self, conn_str='dbname=cuny_courses'):
    """ If proxy server is not running or USE_LOCAL_DB is set, use local db
        Else bind to GAE db through the proxy server.
    """

    # is the proxy server running? (If so, it liatens on port 5431)
    s = socket.socket()
    try:
      s.bind(('localhost', 5431))
      proxy_running = True
    except OSError as e:
      proxy_running = False
    s.close()

    # Check environment override of proxy
    use_local = 'USE_LOCAL_DB' in os.environ.keys()

    if proxy_running and not use_local:
      conn_str += """
                  host=/cloudsql/provost-access-148820:us-east1:cuny-courses
                  user=postgres
                  password=cuny-postgres
                  port=5431
                  """
    self._connection = psycopg2.connect(conn_str)

  # Connection shims
  def commit(self):
    self._connection.commit()

  def close(self):
    self._connection.close()

  # Cursor shim
  # By returning the psycopg2 cursor, there is no need to shim other cursor-based functions.
  def cursor(self, cursor_factory=NamedTupleCursor):
    self._cursor = self._connection.cursor(cursor_factory=cursor_factory)
    return self._cursor
