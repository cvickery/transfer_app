from collections import namedtuple
from pgconnection import pgconnection
from format_rules import format_rule_by_key


# rule_history()
# -------------------------------------------------------------------------------------------------
def rule_history(rule_key):
  """ Generate HTML for the review-history of a transfer rule.
  """
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  cursor.execute("""
      select  s.description,
              e.who,
              e.what,
              to_char(e.event_time, 'YYYY-MM-DD HH12:MI am') as event_time
        from  events e, review_status_bits s
       where  e.rule_id = (select id from transfer_rules
                            where source_institution = %s
                              and destination_institution = %s
                              and subject_area = %s
                              and group_number = %s)
         and  s.abbr = e.event_type
       order by e.event_time desc
                 """, rule_key.split('-'))
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
            <p><a href="/"><button>main menu</button></a></p>
           """.format(rule_key, format_rule_by_key(rule_key)[1], history_rows)
  return result
