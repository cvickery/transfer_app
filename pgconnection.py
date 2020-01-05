#! /usr/bin/env python3
""" Provide postgres db connections from a pool of limited size.
"""
import psycopg2
from psycopg2.pool import ThreadedConnectionPool, PoolError
from psycopg2.extras import NamedTupleCursor

import os
# import re
# import socket

# December 2019
# Use the environment variable DATABASE_URL for the connection string. This makes the app deployable
# to heroku, and is best practice anyway.

# January 2020
# Use a connection pool instead of separate connections for each instance. prompted by trying to
# deploy to an affordable Heroku app.
# Also removed commented-out legacy code used during the good old long-gone Google Application
# Environment days.

# This module was first introduced when the app was deployed to the Google Application Environment.
# I've left that functionality, but commented it out, for historical reference. (See January 2020
# note above.)


class PgConnection():
  """ Return a connection from the pool.
      The cursor will use the NamedTupleCursor cursor_factory unless overridden. It includes shims
      for operational connection functions (commit() and close()).
  """

  _pool = None

  def __init__(self, conn_string='dbname=cuny_courses'):
    """ Get the connection string from the environment and connect to the db.
        Raises PoolError, disguised as a RuntimeError, if connection pool is exhausted.
    """
    # Initialize the pool if not done already
    if PgConnection._pool is None:
      pool_max = os.environ.get('DB_POOL_MAX')
      if pool_max is None:
        pool_max = 10
      conn_string = os.environ.get('DATABASE_URL')
      if conn_string is None:
        conn_string = conn_string
      print(f'PgConnection using up to {pool_max} connections on {conn_string}')
      PgConnection._pool = ThreadedConnectionPool(5, pool_max, conn_string)
    try:
      self._connection = PgConnection._pool.getconn()
    except PoolError as pe:
      raise RuntimeError(pe)
    return

  # Connection shims
  def commit(self):
    self._connection.commit(self)

  def close(self):
    PgConnection._pool.putconn(self._connection)

  # Cursor shim
  # By returning the psycopg2 cursor, there is no need to shim other cursor-based functions.
  # I don't think this is needed.
  def cursor(self, cursor_factory=NamedTupleCursor):
    self._cursor = self._connection.cursor(cursor_factory=cursor_factory)
    return self._cursor
