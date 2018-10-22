""" Attempting to reinvent the wheel for Flask sessions.

    The issue is the size of the session, with too many replacement options to learn. Can I roll my
    own in a reasonable amount of time?

    Plan: sessions is a table in the cuny_courses db. Key-value pairs. Unique keys from
    urandom. Blobs for value. I want the following operations to work, where key is not the db
    key, but is the app's key for an item stored in the db.

    2017-09-06: Migrate to postgres to avoid the persistency problems with sqlite3 in the cloud.

    2017-08-10: Using the (secure) flask session key to hold the MySession session key, but there
    are issues of sessions closing/expiring prematurely.

      mysession = MySession(session)
      mysession[key] = anything
      anything = mysession[key]
      del mysession

    Flask session gets "mysession"
    Purge expired sessions somehow. (low prio: how many user sessions will there actually be%s)
      - The /_sessions entry point does this. But there seem to be a lot of my sessions being
        created.

    I think you have to read the session blob from the db for for each get and both to read and
    write it for each put.

    sqlite> .schema sessions
      CREATE TABLE sessions (
      session_key text primary key,
      session_dict blob,
      expiration_time float);
"""
import time
import datetime
import pickle
import uuid
import logging
from pgconnection import pgconnection

logger = logging.getLogger('mysession')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('debugging.log')
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
# logger.addHandler(fh)
logger.addHandler(sh)

sql_logger = logging.getLogger('postgres')
sql_logger.setLevel(logging.DEBUG)
sfh = logging.FileHandler('debugging.log')
ssh = logging.StreamHandler()
sformatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
sfh.setFormatter(sformatter)
ssh.setFormatter(sformatter)
# sql_logger.addHandler(sfh)
sql_logger.addHandler(ssh)


class MySession:

  def __init__(self, session_key=None):
    """ The constructor establishes a new session in one of three ways:
        1. If called with no session_key, create a new session in the sessions table.
        2. If there is a session_key, and there is an unexpired sessions table entry for it, simply
           clone it.
        3. If there is a session_key, but there is no sessions table entry for it or the session is
           expired, initialize a new session using the provided key, provided the provided key is
           from the same node (hardware address).
    """
    # Debugging constructor during development:
    # logger.debug('*** mysession.__init__(---, {})'.format(session_key))

    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()

    if session_key is None:
      self.session_key = str(uuid.uuid1())
      cursor.execute("insert into sessions values(%s, %s, %s)",
                     (self.session_key,
                      pickle.dumps(dict()),
                      time.time() + datetime.timedelta(minutes=120).total_seconds()))
    else:
      self.session_key = session_key

      # Connect to an existing session. Be sure it exists and hasn't expired
      if self.is_expired(self.session_key):
        # delete expired (or missing) sessions table entry
        cursor.execute('delete from sessions where session_key = %s', (self.session_key,))
        # silently substitute a new uuid if the one provided is not from this machine
        new_uuid = uuid.uuid1()
        if uuid.UUID(self.session_key).node != new_uuid.node:
          logger.warning('UUID from foreign host')
          self.session_key = str(new_uuid)
        # create substitute (empty) session
        cursor.execute("insert into sessions values(%s, %s, %s)",
                       (self.session_key,
                        pickle.dumps(dict()),
                        time.time() + datetime.timedelta(minutes=120).total_seconds()))
      else:
        # Session exists and is not expired: just update its expiration time
        self.touch()
    connection.commit()
    connection.close()

  def __str__(self):
    # logger.debug('*** mysession.__str__({})'.format(self.session_key))
    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()
    cursor.execute("select session_dict from sessions where session_key = %s", (self.session_key,))
    mydict = pickle.loads(cursor.fetchone()[0])
    connection.close()
    self.touch()
    return 'MySession.{} [{}]'.format(self.session_key, ', '.join(mydict.keys()))

  def __del__(self):
    # logger.debug('*** mysession.__del__({})'.format(self.session_key))
    if self.is_expired(self.session_key):
      connection = pgconnection('dbname=cuny_courses')
      cursor = connection.cursor()
      cursor.execute("delete from sessions where session_key = %s", (self.session_key,))
      connection.commit()
      connection.close()

  def __setitem__(self, key, value):
    # logger.debug('*** mysession.__setitem__({}, {}, {}'.format(self.session_key, key, value))
    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()
    cursor.execute("select session_dict from sessions where session_key = %s", (self.session_key,))
    mydict = pickle.loads(cursor.fetchone()[0])
    # logger.debug('  retrieved {} keys from sessions mydict'.format(len(mydict.keys())))
    mydict[key] = value
    # logger.debug('  now mydict has {} keys'.format(len(mydict.keys())))
    cursor.execute("update sessions set session_dict = %s where session_key = %s",
                   (pickle.dumps(mydict), self.session_key))
    connection.commit()
    connection.close()
    self.touch()

  def __getitem__(self, key):
    # logger.debug('*** mysession.__getitem__({}, {})'.format(self.session_key, key))
    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()
    cursor.execute("select session_dict from sessions where session_key = %s", (self.session_key,))
    mydict = pickle.loads(cursor.fetchone()[0])
    connection.close()
    self.touch()
    return mydict[key]  # raise KeyError if key not in session

  def __len__(self):
    # logger.debug('*** mysession.__len__({}'.format(self.session_key))
    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()
    cursor.execute("select session_dict from sessions where session_key = %s", (self.session_key,))
    connection.close()
    mydict = pickle.loads(cursor.fetchone()[0])
    self.touch()
    return len(mydict)

  def __bool__(self):
    # logger.debug('*** mysession.__bool__({})'.format(self.session_key))
    self.touch()
    return True

  def keys(self):
    # logger.debug('*** mysession.keys({})'.format(self.session_key))
    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()
    cursor.execute("select session_dict from sessions where session_key = %s", (self.session_key,))
    mydict = pickle.loads(cursor.fetchone()[0])
    connection.close()
    self.touch()
    return [key for key in mydict]

  def remove(self, key):
    # logger.debug('*** mysession.remove({}, {})'.format(self.session_key, key))
    self.touch()
    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()
    cursor.execute("select session_dict from sessions where session_key = %s", (self.session_key,))
    mydict = pickle.loads(cursor.fetchone()[0])
    if key in mydict:
      del mydict[key]
      cursor.execute("update sessions set session_dict = %s where session_key = %s",
                     (pickle.dumps(mydict), self.session_key))
      connection.commit()
      connection.close()
      return True
    connection.close()
    return False

  def is_expired(self, session_key):
    # logger.debug('*** mysession.is_expired({}, {})'.format(self.session_key, session_key))
    if session_key is None:
      return true

    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()
    cursor.execute("select expiration_time from sessions where session_key = %s", (session_key,))
    row = cursor.fetchone()
    connection.close()
    if row is None or len(row) == 0:
      return True
    expiration_time = row[0]
    if expiration_time is not None and expiration_time > time.time():
      # logger.debug('  returning False')
      return False
    # logger.debug('  returning True')
    return True

  def touch(self):
    # logger.debug('*** mysession.touch({})'.format(self.session_key))
    connection = pgconnection('dbname=cuny_courses')
    cursor = connection.cursor()
    cursor.execute("""
        update sessions set expiration_time = %s where session_key = %s
        """,(time.time() + datetime.timedelta(minutes=120).total_seconds(), self.session_key,))
    connection.commit()
    connection.close()
