from time import sleep
from system_status import (
    get_status,
    get_reason,
    app_unavailable,
    start_update_db,
    end_update_db,
    start_maintenance,
    end_maintenance,
)

print(f"{get_status()}: {get_reason()}".replace("\n", "###"))

print("Starting maintenance")
start_maintenance()
print(f"{get_status()}: {get_reason()}".replace("\n", "###"))

print("Ending maintenance")
end_maintenance()
print(f"{get_status()}: {get_reason()}".replace("\n", "###"))

print("Starting update_db")
start_update_db()
print(f"{get_status()}: {get_reason()}".replace("\n", "###"))

print("Ending update_db")
end_update_db()
print(f"{get_status()}: {get_reason()}".replace("\n", "###"))

print("Starting update_db")
start_update_db()
print("Starting maintenance")
start_maintenance()

print("""Loop while app unavailable. Run these commands to exit:
  $ redis-cli -h localhost set maintenance_started 0
  $ redis-cli -h localhost set update_db_started 0""")
while app_unavailable():
    print(f"{get_status()}: {get_reason()}".replace("\n", "###"))
    sleep(15)

end_update_db()
end_maintenance()
print(f"{get_status()}: {get_reason()}".replace("\n", "###"))
