"""
  Functions for creating review events, updating rule statuses, and generating associated
  reports. Or maybe just for converting pending reviews to events and statuses.
"""
import json
from datetime import datetime
from collections import namedtuple

from pgconnection import pgconnection
from cuny_course import CUNYCourse

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
  conn = pgconnection('dbname=cuny_courses')
  with conn.cursor() as cursor:

    event_type_bits = dict()
    cursor.execute('select * from review_status_bits')
    for row in cursor.fetchall():
      abbr_to_bitmask[row['abbr']] = row['bitmask']
      bitmask_to_description[row['bitmask']] = row['description']
  review_status_bits = True

def status_string(status):
  """
    Generate a string summarizing all bits that are set in status.
  """
  global review_status_bits
  global bitmask_to_description
  if not review_status_bits:
    populate_review_status_bits()
  if status == 0: return 'Not Yet Reviewed'

  strings = []
  bit = 1
  for i in range(16):
    if status & bit: strings.append(bitmask_to_description[bit])
    bit += bit
  return '; '.join(strings)


def process_pending(row):
  """ Look up the token and generate events. Return as status message.
  """
  global review_status_bits
  global abbr_to_bitmask
  if not review_status_bits:
    populate_review_status_bits()
  token = row['token']
  reviews = json.loads(row['reviews'])
  email = row['email']
  when_entered = row['when_entered']
  summaries = ''

  conn = pgconnection('dbname=cuny_courses')
  with conn.cursor() as cursor:

    for review in reviews:

      # Generate an event for this review
      event_type = review['event_type']
      source_institution, discipline, group_number, destination_institution = \
          review['rule_id'].split('-')
      what = review['comment_text']
      q = """
      insert into events (event_type,
                          source_institution,
                          discipline,
                          group_number,
                          destination_institution,
                          who, what, event_time)
                         values (%s, %s, %s, %s, %s, %s, %s, %s)"""
      cursor.execute(q, (event_type,
                         source_institution,
                         discipline,
                         group_number,
                         destination_institution,
                         email,
                         what,
                         when_entered))

      # Update the review state for this rule.
      cursor.execute("""
                     select * from rule_groups
                      where source_institution = %s
                        and discipline = %s
                        and group_number = %s
                        and destination_institution = %s
                     """, (source_institution, discipline, group_number, destination_institution))
      rows = cursor.fetchall()
      if len(rows) != 1:
        summaries = """
        <tr><td class="error">Found {} transfer rules for {}</td></tr>
        """.format(len(rows), rule_id)
        break
      old_status = rows[0]['status']
      new_status = old_status | abbr_to_bitmask[event_type]
      q = """update rule_groups set status = %s
              where source_institution = %s
                and discipline = %s
                and group_number = %s
                and destination_institution = %s"""
      cursor.execute(q, (new_status,
                         source_institution,
                         discipline,
                         group_number,
                         destination_institution))

      # Generate a summary of this review
      old_status_str = status_string(old_status)
      new_status_str = status_string(new_status)
      # Convert to event-history link for the rule
      new_status_str = """
      <a href="/history/{}" target="_blank">{}</a>""".format(review['rule_id'],
                                                             new_status_str)
      summaries += """
      <tr>
        <td><table>{}</table></td>
        <td>{}</td>
        <td>{}</td>
      </tr>
      """.format(review['rule_str'],
                 old_status_str,
                 new_status_str)
    # Remove record from pending_reviews
    cursor.execute('delete from pending_reviews where token = %s', (token, ))

    conn.commit()
    conn.close()

    suffix = 's'
    if len(reviews) == 1: suffix = ''
    return """
    <p>Recorded {} review{} made by <em>{}</em> on {}.</p>
      <table>
        <tr>
          <th>Rule</th>
          <th>Previous Review Status</th>
          <th>New Review Status<br/><em>Click for Review History</em></th>
        </tr>
        {}
      </table>
      """.format(len(reviews),
                 suffix,
                 email,
                 when_entered.strftime('%B %d, %Y at %I:%M %p'),
                 summaries)

# rule_history()
# -------------------------------------------------------------------------------------------------
def rule_history(rule_key):
  """ Generate HTML for the review history of a transfer rule.
  """
  source_institution, discipline, group_number, destination_institution = rule_key.split('-')
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  q = """
      select  r.description,
              e.who,
              e.what,
              to_char(e.event_time, 'YYYY-MM-DD HH12:MI am') as event_time
       from events e, review_status_bits r
       where e.source_institution = %s
         and e.discipline = %s
         and e.group_number = %s
         and e.destination_institution = %s
         and r.abbr = e.event_type
         order by e.event_time desc
      """
  cursor.execute(q, (source_institution, discipline, group_number, destination_institution))
  Event = namedtuple('Event', [d[0] for d in cursor.description])
  history_rows = ''
  if cursor.rowcount < 1:
    history_rows='<tr><td colspan="3">There is no review history for this rule</td></tr>'
  else:
    for event in map(Event._make, cursor.fetchall()):
      what = '<div class="history-what-type">{}</div> {}'.format(event.description, event.what)
      history_rows += """
        <tr>
          <td>{}</td>
          <td>{}</td>
          <td>{}</td>
        </tr>
        """.format(event.event_time.replace(' 0', ' '), event.who, what)
  cursor.close()
  conn.close()
  result = """
            <h1>Event History for Transfer Rule ID {}</h1>
            <table>
              <tr>
                <th>When</th>
                <th>Who</th>
                <th>What</th>
              </tr>
              {}
            </table>
           """.format(rule_key, history_rows)
  return result
