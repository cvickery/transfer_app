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
      pool_max = os.environ.get('DB_POOL_MAX')  # Try to stay in Heroku hobby-basic tier limit
      if pool_max is None:
        pool_max = 95  # Default max_connections in postgresql.conf is 100
      else:
        pool_max = int(pool_max)
      dsn = os.getenv('DATABASE_URL')
      if dsn is None:
        dsn = conn_string
      PgConnection._pool = ThreadedConnectionPool(2, pool_max, dsn)
    try:
      print('connect:', self)
      self._connection = PgConnection._pool.getconn()
    except PoolError as pe:
      raise RuntimeError(pe)
    return

  def __repr__(self):
    return (f'{PgConnection._pool} =>'
            f' min: {PgConnection._pool.minconn}; max: {PgConnection._pool.maxconn}'
            f' num: {len(PgConnection._pool._pool)}; used: {len(PgConnection._pool._used)}')

  # Connection shims
  def commit(self):
    self._connection.commit()

  def close(self):
    PgConnection._pool.putconn(self._connection)
    print('close:', self)

  # Cursor shim
  # By returning the psycopg2 cursor, there is no need to shim other cursor-based functions.
  # I don't think this is needed.
  def cursor(self, cursor_factory=NamedTupleCursor):
    self._cursor = self._connection.cursor(cursor_factory=cursor_factory)
    return self._cursor
