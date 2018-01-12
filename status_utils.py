
from pgconnection import pgconnection

# Copy of the review_status_bits table
# value: bitmask
# abbr: short text
# description: long text
review_status_bits = False
bitmask_to_description = dict()
abbr_to_bitmask = dict()

def populate_review_status_bits():
  """ Define dicts for looking up status bit information.
      bitmask_to_description
      abbr_to_description
  """
  global review_status_bits
  global bitmask_to_description
  global abbr_to_description
  if not review_status_bits:
    conn = pgconnection('dbname=cuny_courses')
    with conn.cursor() as cursor:

      event_type_bits = dict()
      cursor.execute('select * from review_status_bits')
      for row in cursor.fetchall():
        abbr_to_bitmask[row['abbr']] = row['bitmask']
        bitmask_to_description[row['bitmask']] = row['description']
    review_status_bits = True

def get_abbr_to_bitmask():
  global abbr_to_bitmask
  populate_review_status_bits()
  return abbr_to_bitmask

def status_string(status):
  """
    Generate a string summarizing all bits that are set in status.
  """
  global bitmask_to_description
  populate_review_status_bits()
  if status == 0: return 'Not Yet Reviewed'

  strings = []
  bit = 1
  for i in range(16):
    if status & bit: strings.append(bitmask_to_description[bit])
    bit += bit
  return '; '.join(strings)
