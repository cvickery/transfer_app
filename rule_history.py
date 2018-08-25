from collections import namedtuple
from pgconnection import pgconnection
from format_rules import format_rule, rule_ids


# rule_history()
# -------------------------------------------------------------------------------------------------
def rule_history(rule_key):
  """ Generate HTML for the review history of a transfer rule.
  """
  rule_id = rule_ids[rule_key]
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  cursor.execute("""
                 select  r.*, s.source_course_ids, d.destination_course_ids
                   from  transfer_rules r, view_source_courses s, view_destination_courses d
                  where  r.id = %s
                    and  r.id = s.rule_id
                    and  r.id = d.rule_id
                 """, (rule_id, ))
  rule = cursor.fetchone()
  q = """
        select  s.description,
                e.who,
                e.what,
                to_char(e.event_time, 'YYYY-MM-DD HH12:MI am') as event_time
          from  events e, review_status_bits s
         where  e.rule_id = %s
           and  s.abbr = e.event_type
       order by e.event_time desc
      """
  cursor.execute(q, (rule_id, ))
  history_rows = ''
  if cursor.rowcount < 1:
    history_rows = '<tr><td colspan="3">There is no review history for this rule</td></tr>'
  else:
    for event in cursor.fetchall():
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
           """.format(rule_key, format_rule(rule)[1], history_rows)
  return result
