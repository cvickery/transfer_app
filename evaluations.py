"""
  Functions for creating evaluation events, updating rule statuses, and generating associated
  reports. Or maybe just for converting pending evaluations to events and statuses.
"""
import json
from datetime import datetime

from pgconnection import pgconnection

event_type_bits = None
status_messages = None

def status_string(status):
  """
    Generate a string summarizing all bits that are set in status.
  """
  global status_messages
  if status == 0: return 'Not Evaluated'

  if status_messages == None:
    conn = pgconnection('dbname=cuny_courses')
    with conn.cursor() as curr:
      status_messages = dict()
      curr.execute('select * from transfer_rule_status')
      for row in curr.fetchall():
        status_messages[row['value']] = row['description']

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
  with conn.cursor() as curr:

    event_type_bits = dict()
    curr.execute('select * from event_types')
    for row in curr.fetchall():
      event_type_bits[row['abbr']] = row['bitmask']

    status_messages = dict()
    curr.execute('select * from transfer_rule_status')
    for row in curr.fetchall():
      status_messages[row['value']] = row['description']

    for evaluation in evaluations:

      # Generate an event for this evaluation
      event_type = evaluation['event_type']
      src_id = evaluation['rule_src_id']
      dest_id = evaluation['rule_dest_id']
      what = evaluation['comment_text']
      q = """
      insert into events (event_type, src_id, dest_id, who, what, event_time)
                         values (%s, %s, %s, %s, %s, %s)"""
      curr.execute(q, (event_type, src_id, dest_id, email, what, when_entered))

      # Update the evaluation state for this rule.
      source_course_id = evaluation['rule_src_id']
      destination_course_id = evaluation['rule_dest_id']
      curr.execute("""
        select * from transfer_rules
         where source_course_id = %s
           and destination_course_id = %s
        """, (source_course_id, destination_course_id))
      rows = curr.fetchall()
      if len(rows) != 1:
        summaries = """
        <tr><td class="error">Found {} transfer rules for {}:{}</td></tr>
        """.format(source_course_id, destination_course_id)
        break
      old_status = rows[0]['status']
      new_status = old_status | event_type_bits[event_type]
      q = """
        update transfer_rules set status = %s
        where source_course_id = %s
          and destination_course_id = %s
        """
      curr.execute(q, (new_status, source_course_id, destination_course_id))

      # Generate a summary of this evaluation
      old_status_str = status_string(old_status)
      new_status_str = status_string(new_status)
      # Convert to event-history link for the rule
      new_status_str = """
      <a href="/history/{}" target="_blank">{}</a>""".format(evaluation['rule_index'],
                                                             new_status_str)
      summaries += """
      <tr>
        <td title="{} => {}">{}</td>
        <td>{}</td>
        <td>{}</td>
        <td>{}</td>
        <td>{}</td>
      </tr>
      """.format(evaluation['rule_src_id'],
                 evaluation['rule_dest_id'],
                 evaluation['rule_str'],
                 evaluation['event_type'],
                 evaluation['comment_text'],
                 old_status_str, new_status_str)
    # Remove record from pending_evaluations
    curr.execute('delete from pending_evaluations where token = %s', (token, ))

  conn.commit()
  conn.close()
  suffix = 's'
  if len(evaluations) == 1: suffix = ''
  return """
  <p>Recorded {} evaluation{} made by <em>{}</em> on {}.</p>
    <table>
      <tr>
      <th>Rule</th><th>Action</th><th>Note</th><th>Previous Status</th>
      <th>New Status<br/><em>Click for Evaluation History</em></th>
      </tr>
      {}
    </table>
    """.format(len(evaluations),
               suffix,
               email,
               when_entered.strftime('%B %d, %Y at %I:%M %p'), summaries)

# rule_history()
# -------------------------------------------------------------------------------------------------
def rule_history(rule):
  """ Generate HTML for the evaluation history of a transfer rule.
  """
  conn = pgconnection('dbname=cuny_courses')
  curr = conn.cursor()
  try:
    source_course_id, destination_course_id = rule.split(':')
  except ValueError:
    return """
    <h1 class="error">“{}” is not a valid transfer rule. Must be <em>nnn</em>:<em>nnn</em></h1>
    """.format(rule)
  curr.execute("""
    select status from transfer_rules where source_course_id = %s and destination_course_id = %s
    """, (source_course_id, destination_course_id))
  rows = curr.fetchall()
  if len(rows) == 0:
    return '<h1 class="error">{} is not a recognized transfer rule.</h1>'.format(rule)
  status = rows[0]['status']
  status_str = status_string(status)

  # Get the institutions, disciplines, numbers, and titles of the two courses
  description = '<span class="error">[Rule description will go here]</span>'
  result = '<h2>Rule: {}</h2>'.format(description)
  result += '<h2>Status: {}</h2><h2>Evaluation History</h2>'.format(status_str)
  # Get all the events for the transfer rule
  if status == 0:
    result += '<p>This rule has not been evaluated yet.</p>'
  else:
    result += '<table><tr><th>What</th><th>Comment</th><th>Who</th><th>When</th></tr>'
    q = 'select * from events where src_id = %s and dest_id = %s order by event_time'
    curr.execute(q, (source_course_id, destination_course_id))
    for row in curr.fetchall():
      result += """
      <tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>
      """.format(row['event_type'],
                 row['what'],
                 row['who'],
                 row['event_time'].strftime('%B %d, %Y at %I:%M %p'))
    result += '</table>'
  return result
