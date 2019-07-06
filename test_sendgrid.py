#! /usr/local/bin/python3
import os
from pprint import pprint
from sendgrid import SendGridAPIClient

import psycopg2
from psycopg2.extras import NamedTupleCursor

conn = psycopg2.connect('dbname=cuny_courses')
cursor = conn.cursor(cursor_factory=NamedTupleCursor)
cursor.execute('select * from person_roles')
people = dict()
for person in cursor.fetchall():
  people[person.role] = {'name': person.name, 'email': person.email}

message = {'personalizations': [{'to': [people['webmaster']],
                                 # 'cc': [{'email': 'cvickery@gmail.com',
                                 #        'name': 'Test at Google'},
                                 #        {'name': 'CC Tester',
                                 #         'email': 'Christopher.Vickery@qc.cuny.edu'}],
                                 # 'bcc': [{'email': 'poffice@qc.cuny.edu', 'name': 'QC Provost'}],
                                 'subject': 'Testing SendGrid'}],
           'from': {'email': 'cvickery@qc.cuny.edu',
                    'name': 'CUNY Transfer App'},
           'content': [{'type': 'text/plain',
                        'value': 'Don’t worry at all.'},
                       {'type': 'text/html',
                        'value': '<h1>It’s Good</h1>'}]
           }


def send_message(message):
  try:
    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    response = sg.send(message)
    print(response.status_code)
    print(response.body)
    print(response.headers)
  except Exception as e:
    print(e)
# $ test_sendgrid.py
# {'content': [{'type': 'text/plain', 'value': 'Don’t worry at all.'},
#              {'type': 'text/html',
#               'value': '\n'
#                        '<html><head>\n'
#                        '<style>\n'
#                        'table {\n'
#                        '  border-collapse: collapse;\n'
#                        '  border: 1px solid blue;\n'
#                        '}\n'
#                        'td, th {\n'
#                        '  border: 1px solid red;\n'
#                        '  padding: 0.25em;\n'
#                        '}\n'
#                        '</style>\n'
#                        '  </head>\n'
#                        '  <body>\n'
#                        '<p>The following 1 transfer rule review has been '
#                        'submitted by <em>cvickery@qc.cuny.edu</em> on July 03, '
#                        '2019 at 06:17 PM.</p>\n'
#                        '    <table>\n'
#                        '      <tr>\n'
#                        '        <th>Rule</th>\n'
#                        '        <th>Previous Review Status</th>\n'
#                        '        <th>New Review Status<br/><em>Click for Review '
#                        'History</em></th>\n'
#                        '      </tr>\n'
#                        '\n'
#                        '    <tr>\n'
#                        '      <td><table><tr class="rule "><td '
#                        'title="Queensborough">QCC</td><td>Pass <span '
#                        'title="course_id=71">ARTH 115</span></td><td>3.0 =&gt; '
#                        '3.0</td><td title="Queens">QNS</td><td><span '
#                        'title="Art History">ARTH</span>-<span title="course '
#                        'id: 3974">113</span></td></tr></table></td>\n'
#                        '      <td>Sender Approved</td>\n'
#                        '      <td>\n'
#                        '    <a '
#                        'href="http://localhost:5000/history/QCC01-QNS01-AR-13" '
#                        'target="_blank">Sender Approved</a></td>\n'
#                        '    </tr>\n'
#                        '    </table></body>\n'}],
#  'from': {'email': 'cvickery@qc.cuny.edu', 'name': 'CUNY Transfer App'},
#  'personalizations': [{'bcc': [{'email': 'poffice@qc.cuny.edu',
#                                 'name': 'QC Provost'}],
#                        'cc': [{'email': 'cvickery@gmail.com',
#                                'name': 'Test at Google'},
#                               {'email': 'christopher.vickery@qc.cuny.edu',
#                                'name': 'Test at QC'}],
#                        'subject': 'Testing SendGrid',
#                        'to': [{'email': 'cvickery@qc.cuny.edu',
#                                'name': 'Test Recipient'}]}]}
# 202

# 127.0.0.1 - - [03/Jul/2019 23:50:48] "POST /review_rules/ HTTP/1.1" 200 -
# {'content': [{'type': 'text/plain',
#               'value': 'The following 1 transfer rule review has been '
#                        'submitted by\n'
#                        '_cvickery@qc.cuny.edu_ on July 03, 2019 at 11:50 PM.\n'
#                        '\n'
#                        'Rule | Previous Review Status | New Review Status  \n'
#                        ' _Click for Review History_  \n'
#                        '---|---|---  \n'
#                        '|  QNS| Pass ANTH 2| 3.0 => 3.0| QCC| ELEC-1000  \n'
#                        '---|---|---|---|---  \n'
#                        'Not Yet Reviewed |  [Sender\n'
#                        'Approved](http://localhost:5000/history/QNS01-QCC01-ANTH-3)\n'
#                        '\n'},
#              {'type': 'text/html',
#               'value': '\n'
#                        '  <p>The following 1 transfer rule review has been '
#                        'submitted by <em>cvickery@qc.cuny.edu</em> on July 03, '
#                        '2019 at 11:50 PM.</p>\n'
#                        '    <table>\n'
#                        '      <tr>\n'
#                        '        <th>Rule</th>\n'
#                        '        <th>Previous Review Status</th>\n'
#                        '        <th>New Review Status<br/><em>Click for Review '
#                        'History</em></th>\n'
#                        '      </tr>\n'
#                        '      \n'
#                        '    <tr>\n'
#                        '      <td><table><tr class="rule "><td '
#                        'title="Queens">QNS</td><td>Pass <span '
#                        'title="course_id=116848">ANTH 2</span></td><td>3.0 '
#                        '=&gt; 3.0</td><td '
#                        'title="Queensborough">QCC</td><td><span '
#                        'title="Elective Credit">ELEC</span>-<span '
#                        'title="course id: '
#                        '126608">1000</span></td></tr></table></td>\n'
#                        '      <td>Not Yet Reviewed</td>\n'
#                        '      <td>\n'
#                        '    <a '
#                        'href="http://localhost:5000/history/QNS01-QCC01-ANTH-3" '
#                        'target="_blank">Sender Approved</a></td>\n'
#                        '    </tr>\n'
#                        '    \n'
#                        '    </table>\n'
#                        '    '}],
#  'from': {'email': 'cvickery@qc.cuny.edu', 'name': 'CUNY Transfer App'},
#  'personalizations': [{'bcc': [{'email': 'cvickery@qc.cuny.edu',
#                                 'name': 'Christopher Vickery'}],
#                        'cc': [{'email': 'cvickery@qc.cuny.edu',
#                                'name': 'University Registrar'}],
#                        'subject': 'Transfer Rule Evaluation Received',
#                        'to': [{'email': 'cvickery@qc.cuny.edu',
#                                'name': 'Alicia Alvarez'}]}]}
# 127.0.0.1 - - [03/Jul/2019 23:51:01] "GET /confirmation/7c743596-a2e7-4ee8-8c54-bb2e7c4236d7 HTTP/1.1" 200 -


html_value = """
<html><head>
<style>
table {
  border-collapse: collapse;
  border: 1px solid blue;
}
td, th {
  border: 1px solid red;
  padding: 0.25em;
}
</style>
  </head>
  <body>
<p>The following transfer rule review has been submitted by <em>cvickery@qc.cuny.edu</em> on July 03, 2019 at 06:17 PM.</p>
    <table>
      <tr>
        <th>Rule</th>
        <th>Previous Review Status</th>
        <th>New Review Status<br/><em>Click for Review History</em></th>
      </tr>

    <tr>
      <td><table><tr class="rule "><td title="Queensborough">QCC</td><td>Pass <span title="course_id=71">ARTH 115</span></td><td>3.0 =&gt; 3.0</td><td title="Queens">QNS</td><td><span title="Art History">ARTH</span>-<span title="course id: 3974">113</span></td></tr></table></td>
      <td>Sender Approved</td>
      <td>
    <a href="http://localhost:5000/history/QCC01-QNS01-AR-13" target="_blank">Sender Approved</a></td>
    </tr>
    </table></body>
"""

if __name__ == '__main__':
  # message['personalizations'][0]['cc'] = [{'email': 'cvickery@gmail.com',
  #                                          'name': 'Test at Google'},
  #                                         {'name': 'Test at QC',
  #                                          'email': 'christopher.vickery@qc.cuny.edu'}]
  # message['personalizations'][0]['bcc'] = [{'email': 'poffice@qc.cuny.edu', 'name': 'QC Provost'}]
  # message['content'][1] = {'type': 'text/html', 'value': html_value}
  pprint(message)
  send_message(message)
