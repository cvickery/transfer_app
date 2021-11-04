#! /usr/bin/env python3
""" Provide postgres db connections from a pool of limited size.
"""
import psycopg
from psycopg.rows import namedtuple_row

import os
import sys

DEBUG = os.getenv('DEBUG')

# This is a newer version, based on psycopg3. It should remain compatible with previous versions.
# No pool support

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
  """ This version is just a set of shims for psycopg, with default values for the database name
      and row_factory.
      This implementation does NOT support the context manager features of psycopg; it just works
      like psycopg2. New code should use psycopg, psycopg.rows, and possibly psycopg.pools directly.
  """
  def __init__(self, dbname='cuny_curriculum'):
    self.conn = psycopg.connect(conninfo=f'dbname={dbname}')

  def cursor(self, factory_name=namedtuple_row):
    return self.conn.cursor(row_factory=factory_name)

  def close(self):
    self.conn.close()

  def commit(self):
    self.conn.commit()
