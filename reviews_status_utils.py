from typing import Dict
import psycopg
from psycopg.rows import namedtuple_row

# Copy of the review_status_bits table
# value: bitmask
# abbr: short text
# description: long text

# Dicts for looking up status bit information.

bitmask_to_description: Dict[int, str] = dict()
abbr_to_bitmask: Dict[str, int] = dict()
event_type_bits: Dict[int, str] = dict()

with psycopg.connect('dbname=cuny_curriculum') as conn:
  with conn.cursor(row_factory=namedtuple_row) as cursor:
    cursor.execute('select * from review_status_bits')
    for row in cursor.fetchall():
      abbr_to_bitmask[row.abbr] = row.bitmask
      bitmask_to_description[row.bitmask] = row.description


def get_abbr_to_bitmask():
  return abbr_to_bitmask


def status_string(status):
  """
    Generate a string summarizing all bits that are set in status.
  """
  if status == 0:
    return 'Not Yet Reviewed'

  strings = []
  bit = 1
  for i in range(16):
    if status & bit:
      strings.append(bitmask_to_description[bit])
    bit += bit
  return '; '.join(strings)
