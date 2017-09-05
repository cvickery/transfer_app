import psycopg2
import psycopg2.extras
import os
import re
import socket

class pgconnection:
  """
      Wrappers for psycopg2 connect() and cursor(). The former handles connection to local (testing)
      db or remote, based on environment variables and whether proxy server is detected or not. The
      latter takes care of using the DictCursor cursor factory for the connection. Includes shims
      for operational connection functions (commit() and close()).
  """
  # Use psycopg2.connect() to access local (testing) db or the master copy
  def __init__(self, str):
    """ Connect to local db, use proxy, or connect directly.
        If USE_LOCAL_DB is set, connect that db locally (default user, etc.)
        Otherwise, use /cloudsql... with PGPORT, which will be 5431 if the proxy server
        is running.
    """
    dbname = os.environ.get('USE_LOCAL_DB')
    if dbname != None:
      self._connection = psycopg2.connect('dbname={}'.format(dbname))
      return

    # Extract the dbname from the connection string and set up for deployed GAE access
    dbname = re.search('dbname=(\w*)', str).group(1)
    port = 5432
    host = '/cloudsql/provost-access-148820:us-east1:cuny-courses'
    user = 'postgres'
    password = 'cuny-postgres'
    # if port 5431 is bound, the proxy is running, and the connection string refers to localhost on
    # that port
    s = socket.socket()
    try:
      c = s.bind(('localhost', 5431))
    except:
      # Unable to bind: proxy must be running
      host = 'localhost'
      port = 5431
    s.close()
    conn_str = 'dbname={} host={} port={} user={} password={}'.format(
        dbname,
        host,
        port,
        user,
        password)
    self._connection = psycopg2.connect(conn_str)

  # Connection shims
  def commit(self):
    self._connection.commit()

  def close(self):
    self._connection.close()

  # Cursor shim
  # By returning the psycopg2 cursor, there is no need to shim other cursor-based functions.
  def cursor(self):
    self._cursor = self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    return self._cursor
