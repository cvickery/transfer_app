# Manage status of system:
#   APP_AVAILABLE: True with system is not available. Normally, just means db is being updated, but
#   could be something more drastic.

from time import perf_counter

APP_AVAILABLE = True
_start_update = None
_start_maintenance = None


# app_available()
# -------------------------------------------------------------------------------------------------
def app_available():
  """ Tell whether app is unavailable due to db update or maintenance.
  """
  global APP_UNAVAILABLE
  return APP_AVAILABLE


# app_unavailable()
# -------------------------------------------------------------------------------------------------
def app_unavailable():
  """ Tell whether app is unavailable due to db update or maintenance.
  """
  global APP_UNAVAILABLE
  return not APP_AVAILABLE


# get_reason()
# -------------------------------------------------------------------------------------------------
def get_reason():
  """ Explain app availability.
  """
  global APP_AVAILABLE, _is_update, _is_maintenance
  if APP_AVAILABLE:
    return 'Application is available.'

  return_val = ''

  if _start_update:
    time_remaining = perf_counter() - (_start_update + 1800.0)
    mins_remaining = abs(int(time_remaining / 60))
    secs_remaining = abs(time_remaining) - (mins_remaining * 60)
    if time_remaining < 0.0:
      when = f'complete within {mins_remaining}:{int(secs_remaining):02} min:sec.'
    else:
      when = f'have completed {mins_remaining}:{int(secs_remaining):02} min:sec ago.'
    return_val = f'<h2>Database update should {when}</h2>'

  if _start_maintenance:
    time_elapsed = perf_counter() - _start_maintenance
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
  global APP_AVAILABLE, _start_update
  APP_AVAILABLE = False
  _start_update = perf_counter()
  return APP_AVAILABLE


# end_update_db()
# -------------------------------------------------------------------------------------------------
def end_update_db():
  """ Make app available when db update ends, unless maintenance in progress.
  """
  global APP_AVAILABLE, _start_update, _start_maintenance
  _start_update = None
  if _start_maintenance:
    APP_AVAILABLE = False
  else:
    APP_AVAILABLE = True
  return APP_AVAILABLE


# start_maintenance()
# -------------------------------------------------------------------------------------------------
def start_maintenance():
  """ Make app unavailable: unspecified maintenance in progress.
  """
  global APP_AVAILABLE, _start_maintenance
  APP_AVAILABLE = False
  _start_maintenance = perf_counter()
  return APP_AVAILABLE


# end_maintenance()
# -------------------------------------------------------------------------------------------------
def end_maintenance():
  """ End maintenance mode: app is available unless db update in progress
  """
  global APP_AVAILABLE, _start_maintenance, _start_update
  APP_AVAILABLE = True
  _start_maintenance = None
  if _start_update:
    APP_AVAILABLE = False
  else:
    APP_AVAILABLE = True
  return APP_AVAILABLE
