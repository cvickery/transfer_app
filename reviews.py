"""
  Functions for creating review events, updating rule statuses, and generating associated
  reports. Or maybe just for converting pending reviews to events and statuses.
"""
import json
from datetime import datetime
from collections import namedtuple

from pgconnection import pgconnection
from format_rules import format_rule
from status_utils import abbr_to_bitmask, status_string


def process_pending(row):
  """ Look up the token and generate events. Return as status message.
  """
  token = row['token']
  reviews = json.loads(row['reviews'])
  email = row['email']
  when_entered = row['when_entered']
  summaries = ''

  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

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
  if len(reviews) == 1:
    suffix = ''
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
