# Manage status of system:
#   APP_AVAILABLE: True with system is not available. Normally, just means db is being updated, but
#   could be something more drastic.

from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import NamedTupleCursor

from time import perf_counter
from memcache import Client

APP_AVAILABLE = True


# get_status()
# -------------------------------------------------------------------------------------------------
def get_status():
  db = psycopg2.connect('dbname=access_control')
  cursor = db.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute('select * from access_control')
  available = not any([x.start_time for x in cursor.fetchall()])
  cursor.close()
  db.commit()
  return available


# app_available()
# -------------------------------------------------------------------------------------------------
def app_available():
  """ Tell whether app is unavailable due to db update or maintenance.
  """
  return get_status()


# app_unavailable()
# -------------------------------------------------------------------------------------------------
def app_unavailable():
  """ Tell whether app is unavailable due to db update or maintenance.
  """
  return not get_status()


# get_reason()
# -------------------------------------------------------------------------------------------------
def get_reason():
  """ Explain app availability.
  """
  return_val = ''

  db = psycopg2.connect('dbname=access_control')
  cursor = db.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute('select * from access_control')
  events = dict([(e.event_type, e.start_time) for e in cursor.fetchall()])
  cursor.close()

  time_now = datetime.now()
  if events['update_db']:
    end_update = events['update_db'] + timedelta(seconds=1800)
    if time_now < end_update:
      time_remaining = end_update - time_now
      when = 'complete within {}:{:02} (min:sec).'
    else:
      time_remaining = time_now - end_update
      when = 'have completed {}:{:02} (min:sec) ago.'
    days = time_remaining.days
    hours, remainder = divmod(time_remaining.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    when = when.format(minutes, seconds)
    return_val = f'<h2>Database update should {when}</h2>'

  if events['maintenance']:
    time_elapsed = time_now - events['maintenance']
    days = time_elapsed.days
    hours, remainder = divmod(time_elapsed.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return_val += f"""<h2>Maintenance began
        {days} days, {hours}:{minutes:02}:{seconds:02} (hr:min:sec) ago.</h2>"""

  if return_val == '':
    return_val = 'Application is available.'
  return return_val


# start_update_db()
# -------------------------------------------------------------------------------------------------
def start_update_db():
  """ Make app unavailable: db update in progress.
  """
  db = psycopg2.connect('dbname=access_control')
  cursor = db.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute("update access_control set start_time = now() where event_type='update_db'")
  cursor.close()
  db.commit()
  return get_status()


# end_update_db()
# -------------------------------------------------------------------------------------------------
def end_update_db():
  """ Make app available when db update ends, unless maintenance in progress.
  """
  db = psycopg2.connect('dbname=access_control')
  cursor = db.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute("update access_control set start_time = NULL where event_type = 'update_db'")
  cursor.close()
  db.commit()
  return get_status()


# start_maintenance()
# -------------------------------------------------------------------------------------------------
def start_maintenance():
  """ Make app unavailable: unspecified maintenance in progress.
  """
  db = psycopg2.connect('dbname=access_control')
  cursor = db.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute("""
                 update access_control set start_time = now() where event_type = 'maintenance'
                 """)
  cursor.close()
  db.commit()
  return get_status()


# end_maintenance()
# -------------------------------------------------------------------------------------------------
def end_maintenance():
  """ End maintenance mode: app is available unless db update in progress
  """
  db = psycopg2.connect('dbname=access_control')
  cursor = db.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute("""
                 update access_control set start_time = NULL where event_type = 'maintenance'
                 """)
  cursor.close()
  db.commit()
  return get_status()
