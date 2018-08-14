from collections import namedtuple
from pgconnection import pgconnection
from format_rules import format_rule


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
         and e.source_discipline = %s
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
            <h1>Transfer Rule {}</h1>
            {}
            <h2>Review History</h2>
            <table>
              <tr>
                <th>When</th>
                <th>Who</th>
                <th>What</th>
              </tr>
              {}
            </table>
           """.format(rule_key, format_rule(rule_key)[1], history_rows)
  return result
