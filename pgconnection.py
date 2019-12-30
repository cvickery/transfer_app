import psycopg2
from psycopg2.extras import NamedTupleCursor

import os
# import re
# import socket

# December 2019
# Move to environment variable DATABASE_URL for the connection string. This makes the app deployable
# to heroku, and is best practice anyway.


# This module was needed when the app was deployed to the Google Application Environment.
# I've left that functionality, but commented it out, for historical reference.


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
  def __init__(self, conn_string='dbname=cuny_courses'):
    """ Get the connection string from the environment and connect to the db.
    """
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL is not None:
      conn_string = DATABASE_URL
    """ Connect to the database. Handles three cases:
        1. Development on local machine (local host, local user, standard port)
        2. Development using GAE database (local host, user postgres, proxy port)
        3. Deployed on GAE (cloud host, user postgres, standard port)
    """
    # Development on local machine using local db?
    # dbname = os.environ.get('USE_LOCAL_DB')
    # if dbname is not None:
    #   self._connection = psycopg2.connect('dbname={}'.format(dbname))
    #   return

    # Connect to the Cloud db from either a development machine or from GAE.
    # Is proxy server running?
    # s = socket.socket()
    # try:
    #   s.bind(('localhost', 5431))
    #   # Port 5431 is available, so the proxy server is not running, which means we
    #   # are running the app on GAE, and need to augment the connection string.
    #   conn_str += """
    #               host=/cloudsql/provost-access-148820:us-east1:cuny-courses
    #               user=postgres
    #               password=cuny-postgres
    #               """
    # except OSError as e:
    #   # Port 5431 is not available, so the proxy server must be running, which means
    #   # we running the app locally, but using the Cloud db.
    #   pass
    # s.close()

    self._connection = psycopg2.connect(conn_string)
    return

  # Connection shims
  def commit(self):
    self._connection.commit()

  def close(self):
    self._connection.close()

  # Cursor shim
  # By returning the psycopg2 cursor, there is no need to shim other cursor-based functions.
  # I don't think this is needed.
  def cursor(self, cursor_factory=NamedTupleCursor):
    self._cursor = self._connection.cursor(cursor_factory=cursor_factory)
    return self._cursor
