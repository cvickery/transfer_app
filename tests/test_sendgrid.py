#! /usr/bin/env python3
import os
import psycopg
from pprint import pprint
from sendgrid import SendGridAPIClient
from psycopg.rows import namedtuple_row

conn = psycopg.connect("dbname=cuny_curriculum")
cursor = conn.cursor(row_factory=namedtuple_row)
cursor.execute("select * from person_roles")
people = dict()
for person in cursor.fetchall():
    people[person.role] = {"name": person.name, "email": person.email}
conn.close()

message = {
    "personalizations": [{"to": [people["webmaster"]], "subject": "Testing SendGrid"}],
    "from": {"email": "christopher.vickery@qc.cuny.edu", "name": "T-Rex Labs"},
    "content": [
        {"type": "text/plain", "value": "Don’t worry at all."},
        {"type": "text/html", "value": "<h1>It’s Good</h1>"},
    ],
}


def send_message(message):
    try:
        sg = SendGridAPIClient(os.environ.get("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)


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
<p>
  The following transfer rule review has been submitted by <em>christopher.vickery@qc.cuny.edu</em>
  on July 03, 2019 at 06:17 PM.
</p>
  <table>
    <tr>
      <th>Rule</th>
      <th>Previous Review Status</th>
      <th>New Review Status<br/><em>Click for Review History</em></th>
    </tr>

  <tr>
    <td>
      <table>
        <tr class="rule ">
        <td title="Queensborough">QCC</td>
        <td>Pass <span title="course_id=71">ARTH 115</span></td>
        <td>3.0 =&gt; 3.0</td><td title="Queens">QNS</td>
        <td><span title="Art History">ARTH</span>-<span title="course id: 3974">113</span></td>
        </tr></table></td>
    <td>Sender Approved</td>
    <td>
  <a href="http://localhost:5000/history/QCC01-QNS01-AR-13" target="_blank">Sender Approved</a></td>
  </tr>
  </table></body>
"""

if __name__ == "__main__":
    pprint(message)
    send_message(message)
