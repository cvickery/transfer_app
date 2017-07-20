""" Attempting to reinvent the wheel for Flask sessions.
    The issue is the size of the session, with too many replacement options to learn. Can I roll my
    own in a reasonable amount of time?

    Plan: sessions is a table in the cuny_courses.db sqlite db. Key-value pairs. Unique keys from
    urandom. Blobs for value. I want the following operations to work, where key is not the db
    key, but is the app's key for an item stored in the db.

      mysession = MySession(session)
      mysession[key] = anything
      anything = mysession[key]
      del mysession

    Flask session gets "mysession"
    purge expired sessions somehow (low prio: how many user sessions will there actually be?)
    use namedtuples for session values

    I think you have to read the session blob from the db for for each get and both to read and
    write it for each put.

    sqlite> .schema sessions
      CREATE TABLE sessions (
      session_key text primary key,
      session_dict blob,
      expiration_time float);
"""
from collections import namedtuple
import time, datetime
import json
from uuid import uuid4
import sqlite3

class MySession:

  def __init__(self, app, session_key=None):
    initialized = False
    self.connection = sqlite3.connect('static/db/cuny_catalog.db')
    self.connection.row_factory = sqlite3.Row
    self.cursor = self.connection.cursor()
    if not session_key:
      self.session_key = str(uuid4())
    else:
      # Attempting to connect to an existing session. Be sure it exists and hasn't expired
      self.session_key = session_key
      self.cursor.execute("select expiration_time from sessions where session_key = '{}'".format(session_key))
      expiration_time = self.cursor.fetchone()[0]
      if expiration_time and expiration_time > time.time():
        initialized = True
      else:
        # Reference to expired session: delete it from db and reinitialize
        if expiration_time:
          self.cursor.execute("delete from sessions where session_key = '{}'".format(session_key))
    if not initialized:
      self.cursor.execute("""
        insert into sessions values('{}', '{}', {})
        """.format(self.session_key,
                   json.dumps(dict()),
                   time.time() + datetime.timedelta(minutes=120).total_seconds()))
    self.connection.commit()

  def __del__(self):
    self.cursor.execute("""
      delete from sessions values where session_key = {}
      """.format(self.session_key))
    self.connection.commit()

  def __setitem__(self, key, value):
    self.cursor.execute("select session_dict from sessions where session_key = '{}'".format(self.session_key))
    mydict = json.loads(self.cursor.fetchone()[0])
    mydict[key] = value
    self.cursor.execute("update sessions set session_dict = '{}' where session_key = '{}'".format(
      json.dumps(mydict), self.session_key))
    self.connection.commit()

  def __getitem__(self, key):
    self.cursor.execute("select session_dict from sessions where session_key = '{}'".format(self.session_key))
    mydict = json.loads(self.cursor.fetchone()[0])
    return mydict[key] # might return KeyError
