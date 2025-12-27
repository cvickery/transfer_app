# Manage status of system:
#   APP_AVAILABLE: True with system is not available. Normally, just means db is being updated, but
#   could be something more drastic.

import os
from datetime import datetime, timedelta
from time import time
import redis

redis_url = os.environ.get("REDIS_URL")
if redis_url is None:
    redis_url = "redis://localhost"
r = redis.from_url(redis_url)

if r.get("update_db_started") is None:
    r.set("update_db_started", 0)
if r.get("maintenance_started") is None:
    r.set("maintenance_started", 0)
APP_AVAILABLE = True


# get_status()
# -------------------------------------------------------------------------------------------------
def get_status():
    maintenance_started = int(r.get("maintenance_started"))
    update_db_started = int(r.get("update_db_started"))
    available = maintenance_started == 0 and update_db_started == 0
    return available


# app_available()
# -------------------------------------------------------------------------------------------------
def app_available():
    """Tell whether app is unavailable due to db update or maintenance."""
    return get_status()


# app_unavailable()
# -------------------------------------------------------------------------------------------------
def app_unavailable():
    """Tell whether app is unavailable due to db update or maintenance."""
    return not get_status()


# get_reason()
# -------------------------------------------------------------------------------------------------
def get_reason():
    """Explain app availability."""
    return_val = ""
    time_now = datetime.now()

    update_db_started = int(r.get("update_db_started"))
    if update_db_started > 0:
        end_update = datetime.fromtimestamp(update_db_started) + timedelta(seconds=3600)
        if time_now < end_update:
            time_remaining = end_update - time_now
            copula = "is"
            when = "within {} minutes."
        else:
            time_remaining = time_now - end_update
            copula = "was"
            when = "{} minutes ago."
        days = time_remaining.days
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes = remainder // 60
        if minutes == 1:
            when = when.replace("{} minutes", "one minute")
        elif minutes == 0:
            when = when.replace("{} minutes", "less than a minute")
        else:
            when = when.format(minutes)
        return_val = f"<h2>Database update {copula} expected to complete {when}</h2>"

    maintenance_started = int(r.get("maintenance_started"))
    if maintenance_started > 0:
        time_elapsed = time_now - datetime.fromtimestamp(maintenance_started)
        days = time_elapsed.days
        hours, remainder = divmod(time_elapsed.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        seconds = min(50, round(seconds, -1))
        return_val += (
            f"<h2>Maintenance began {days} days, "
            f"{hours}:{minutes:02}:{seconds:02} (hr:min:sec) ago.</h2>"
        )

    if return_val == "":
        return_val = "Application is available."
    return return_val


# start_update_db()
# -------------------------------------------------------------------------------------------------
def start_update_db():
    """Make app unavailable: db update in progress."""
    r.set("update_db_started", int(time()))
    return get_status()


# end_update_db()
# -------------------------------------------------------------------------------------------------
def end_update_db():
    """Make app available when db update ends, unless maintenance in progress."""
    r.set("update_db_started", 0)
    return get_status()


# start_maintenance()
# -------------------------------------------------------------------------------------------------
def start_maintenance():
    """Make app unavailable: unspecified maintenance in progress."""
    r.set("maintenance_started", int(time()))
    return get_status()


# end_maintenance()
# -------------------------------------------------------------------------------------------------
def end_maintenance():
    """End maintenance mode: app is available unless db update in progress"""
    r.set("maintenance_started", 0)
    return get_status()
