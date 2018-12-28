# Manage status of system:
#   APP_AVAILABLE: True with system is not available. Normally, just means db is being updated, but
#   could be something more drastic.

from time import perf_counter
from memcache import Client

client = Client(['127.0.0.1:11211'])
client.set('APP_AVAILABLE', True)
client.set('start_update', None)
client.set('start_maintenance', None)


# app_available()
# -------------------------------------------------------------------------------------------------
def app_available():
  """ Tell whether app is unavailable due to db update or maintenance.
  """
  global client
  return client.get('APP_AVAILABLE')


# app_unavailable()
# -------------------------------------------------------------------------------------------------
def app_unavailable():
  """ Tell whether app is unavailable due to db update or maintenance.
  """
  global client
  return not client.get('APP_AVAILABLE')


# get_reason()
# -------------------------------------------------------------------------------------------------
def get_reason():
  """ Explain app availability.
  """
  global client
  if client.get('APP_AVAILABLE'):
    return 'Application is available.'

  return_val = ''

  if client.get('start_update'):
    time_remaining = perf_counter() - (client.get('start_update') + 1800.0)
    mins_remaining = abs(int(time_remaining / 60))
    secs_remaining = abs(time_remaining) - (mins_remaining * 60)
    if time_remaining < 0.0:
      when = f'complete within {mins_remaining}:{int(secs_remaining):02} min:sec.'
    else:
      when = f'have completed {mins_remaining}:{int(secs_remaining):02} min:sec ago.'
    return_val = f'<h2>Database update should {when}</h2>'

  if client.get('start_maintenance'):
    time_elapsed = perf_counter() - client.get('start_maintenance')
    hours_elapsed = int(time_elapsed / 3600)
    mins_elapsed = int((time_elapsed - int(hours_elapsed * 3600)) / 60)
    secs_elapsed = int(time_elapsed - int(hours_elapsed * 3600) - int(mins_elapsed * 60))
    return_val += f"""<h2>Maintenance began
        {hours_elapsed}:{mins_elapsed:02}:{secs_elapsed:02} hr:min:sec ago.</h2>"""

  return return_val


# start_update_db()
# -------------------------------------------------------------------------------------------------
def start_update_db():
  """ Make app unavailable: db update in progress.
  """
  global client
  client.set('APP_AVAILABLE', False)
  client.set('start_update', perf_counter())
  return client.get('APP_AVAILABLE')


# end_update_db()
# -------------------------------------------------------------------------------------------------
def end_update_db():
  """ Make app available when db update ends, unless maintenance in progress.
  """
  global client
  client.set('start_update', None)
  if client.get('start_maintenance'):
    client.set('APP_AVAILABLE', False)
  else:
    client.set('APP_AVAILABLE', True)
  return client.get('APP_AVAILABLE')


# start_maintenance()
# -------------------------------------------------------------------------------------------------
def start_maintenance():
  """ Make app unavailable: unspecified maintenance in progress.
  """
  global client
  client.set('APP_AVAILABLE', False)
  client.set('start_maintenance', perf_counter())
  return client.get('APP_AVAILABLE')


# end_maintenance()
# -------------------------------------------------------------------------------------------------
def end_maintenance():
  """ End maintenance mode: app is available unless db update in progress
  """
  global client
  client.set('start_maintenance', None)
  if client.get('start_update'):
    client.set('APP_AVAILABLE', False)
  else:
    client.set('APP_AVAILABLE', True)
  return client.get('APP_AVAILABLE')
