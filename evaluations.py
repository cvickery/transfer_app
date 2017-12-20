"""
  Functions for creating evaluation events, updating rule statuses, and generating associated
  reports. Or maybe just for converting pending evaluations to events and statuses.
"""
import json
from datetime import datetime
from collections import namedtuple

from pgconnection import pgconnection
from cuny_course import CUNYCourse

event_type_bits = None
status_messages = None

def status_string(status):
  """
    Generate a string summarizing all bits that are set in status.
  """
  global status_messages
  if status == 0: return 'Not Yet Reviewed'

  if status_messages == None:
    conn = pgconnection('dbname=cuny_courses')
    with conn.cursor() as cursor:
      status_messages = dict()
      cursor.execute('select * from transfer_rule_status')
      for row in cursor.fetchall():
        status_messages[row['value']] = row['description']
    conn.close()
  strings = []
  bit = 1
  for i in range(16):
    if status & bit: strings.append(status_messages[bit])
    bit += bit
  return '; '.join(strings)


def process_pending(row):
  """ Look up the token and generate events. Return as status message.
  """
  global event_type_bits, status_messages

  token = row['token']
  evaluations = json.loads(row['evaluations'])
  email = row['email']
  when_entered = row['when_entered']
  summaries = ''
  conn = pgconnection('dbname=cuny_courses')
  with conn.cursor() as cursor:

    event_type_bits = dict()
    cursor.execute('select * from event_types')
    for row in cursor.fetchall():
      event_type_bits[row['abbr']] = row['bitmask']

    status_messages = dict()
    cursor.execute('select * from transfer_rule_status')
    for row in cursor.fetchall():
      status_messages[row['value']] = row['description']

    for evaluation in evaluations:

      # Generate an event for this evaluation
      event_type = evaluation['event_type']
      source_institution, discipline, group_number, destination_institution = \
          evaluation['rule_id'].split('-')
      what = evaluation['comment_text']
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

      # Update the evaluation state for this rule.
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
        """.format(rule_id)
        break
      old_status = rows[0]['status']
      new_status = old_status | event_type_bits[event_type]
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

      # Generate a summary of this evaluation
      old_status_str = status_string(old_status)
      new_status_str = status_string(new_status)
      # Convert to event-history link for the rule
      new_status_str = """
      <a href="/history/{}" target="_blank">{}</a>""".format(evaluation['rule_id'],
                                                             new_status_str)
      summaries += """
      <tr>
        <td><table>{}</table></td>
        <td>{}</td>
        <td>{}</td>
      </tr>
      """.format(evaluation['rule_str'],
                 old_status_str,
                 new_status_str)
    # Remove record from pending_evaluations
    cursor.execute('delete from pending_evaluations where token = %s', (token, ))

  conn.commit()
  cursor.close()
  conn.close()

  suffix = 's'
  if len(evaluations) == 1: suffix = ''
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
    """.format(len(evaluations), suffix, email, when_entered.strftime('%B %d, %Y at %I:%M %p'),
               summaries)

# rule_history()
# -------------------------------------------------------------------------------------------------
def rule_history(rule_key):
  """ Generate HTML for the evaluation history of a transfer rule.
  """
  source_institution, discipline, group_number, destination_institution = rule_key.split('-')
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  q = """
      select event_type, who, what, to_char(event_time, 'YYYY-MM-DD HH12:MI am') as event_time
       from events
       where source_institution = %s
         and discipline = %s
         and group_number = %s
         and destination_institution = %s order by event_time desc
      """
  cursor.execute(q, (source_institution, discipline, group_number, destination_institution))
  Event = namedtuple('Event', [d[0] for d in cursor.description])
  history_rows = ''
  if cursor.rowcount < 1:
    history_rows='<tr><td colspan="3">There is no evaluation history for this rule</td></tr>'
  else:
    for event in map(Event._make, cursor.fetchall()):
      what = '<div class="history-what-type">{}</div> {}'.format(event.event_type, event.what)
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
