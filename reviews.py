"""
  Functions for creating review events, updating rule statuses, and generating associated
  reports. Or maybe just for converting pending reviews to events and statuses.
"""
import json
from datetime import datetime

from pgconnection import pgconnection
from format_rules import format_rule
from reviews_status_utils import abbr_to_bitmask, status_string
from collections import namedtuple

RuleKey = namedtuple('RuleKey', """ source_institution
                                    destination_institution
                                    subject_area
                                    group_number
                                """)


def process_pending(row):
  """ Look up the token and generate events. Return as status message.
  """
  token = row.token
  reviews = json.loads(row.reviews)
  email = row.email
  when_entered = row.when_entered
  summaries = ''

  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

  institutions = set()
  for review in reviews:
    key = RuleKey._make(review['rule_key'].split('-'))
    institutions.add(key.source_institution)
    institutions.add(key.destination_institution)
    cursor.execute("""
      select id, review_status
        from transfer_rules
       where source_institution = %s
         and destination_institution = %s
         and subject_area = %s
         and group_number = %s
      """, key)
    rule_id, old_status = cursor.fetchone()
    # Generate an event for this review
    q = """
    insert into events (rule_id, event_type,
                        who, what, event_time)
                       values (%s, %s, %s, %s, %s)"""
    cursor.execute(q, (rule_id,
                       review['event_type'],
                       email,
                       review['comment_text'],
                       when_entered))

    # Update the review state for this rule.
    new_status = old_status | abbr_to_bitmask[review['event_type']]
    q = 'update transfer_rules set review_status = %s where id = %s'
    cursor.execute(q, (new_status, rule_id))

    # Generate a summary of this review
    old_status_str = status_string(old_status)
    new_status_str = status_string(new_status)
    # Convert to event-history link for the rule
    new_status_str = """
    <a href="/history/{}" target="_blank">{}</a>""".format(review['rule_key'],
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
  if len(reviews) == 1:
    suffix = ''
  # Return summary as an html table, and the set of institutions affected.
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
               summaries), institutions
