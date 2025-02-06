#! /usr/bin/env python3
""" Provide postgres db connections from a pool of limited size.
"""
from psycopg2.pool import ThreadedConnectionPool, PoolError
from psycopg2.extras import NamedTupleCursor

import os
import sys

DEBUG = os.getenv('DEBUG')

# March 2021
# This is a new version, backward compatible with the previous one.
# This version can manage connection pools for multiple databases at a time.
# A PgConnection instance represents a connection from a pool of connections for the specified db.
# The pool is created when the first PgConnection for the db is instantiated.
#   The database name may be specified when the PgConnection is instantiated; the default is
#   cuny_curriculum.
#   Cursors use the NamedTuple cursor_factory by default, but a different one can be specified as
#   an argument to the cursor() method.

# January 2020
# Use a connection pool instead of separate connections for each instance. prompted by trying to
# deploy to an affordable Heroku app.
# Also removed commented-out legacy code used during the good-old long-gone Google Application
# Environment days.

# December 2019
# Use the environment variable DATABASE_URL for the connection string. This makes the app deployable
# to heroku, and is best practice anyway.

# This module was first introduced when the app was deployed to the Google Application Environment.
# I've left that functionality, but commented it out, for historical reference. (See January 2020
# note above.)


# class PgConnection
# -------------------------------------------------------------------------------------------------
class PgConnection():
  """ Get a connection from a pool of connections for the specified database.
      The cursor() method uses the NamedTupleCursor cursor_factory unless overridden.
      Includes shims for psycopg2 connection functions commit() and close().
  """
  # Connection pools, keyed by db name
  _pools = dict()

  def __init__(self, dbname='cuny_curriculum'):
    """ Get the connection string from the environment and connect to the db.
        Raises PoolError, disguised as a RuntimeError, if cthe connection pool is exhausted.
    """
    if os.getenv('DATABASE_NAME') is not None:
      dbname = os.getenv('DATABASE_NAME')
    connection_string = f'dbname={dbname}'
    if DEBUG:
      print(connection_string, file=sys.stderr)

    # Initialize a pool for this db if not available yet.
    if dbname not in PgConnection._pools.keys():
      pool_max = os.environ.get('DB_POOL_MAX')  # Try to stay in Heroku hobby-basic tier limit
      if pool_max is None:
        pool_max = 95  # Value of max_connections in default postgresql.conf is 100
      else:
        pool_max = int(pool_max)
      PgConnection._pools[dbname] = ThreadedConnectionPool(2, pool_max, connection_string)

    # Initialize this PgConnection instance
    try:
      self.dbname = dbname
      self.pool = PgConnection._pools[dbname]
      self.connection = self.pool.getconn()
    except PoolError as pe:
      raise RuntimeError(pe)
    return

  def __repr__(self):
    """ The db name and pool status for this connection.
    """
    return (f'{self.dbname} => '
            f' min: {self.pool.minconn}; max: {self.pool.maxconn} '
            f'num: {len(self.pool._pool)}; used: {len(self.pool._used)}')

  # Connection shims
  # -----------------------------------------------------------------------------------------------
  def commit(self):
    """ Shim for psycopg2 connection.commit()
    """
    self.connection.commit()

  def close(self):
    """ Shim for psycopg2 connection.close()
    """
    self.pool.putconn(self.connection)
    if DEBUG:
      print('close:', self, file=sys.stderr)

  def cursor(self, cursor_factory=NamedTupleCursor):
    """ Shim for psycopg2 connection.cursor()
        By returning a psycopg2 cursor, there is no need to shim other cursor-based functions.
        Default cursor_factory is psycopg2.extras.NamedTupleCursor.
    """
    return self.connection.cursor(cursor_factory=cursor_factory)
