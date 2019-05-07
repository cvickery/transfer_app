import os
import sendgrid
from sendgrid.helpers import mail


def send_token(email, url, evaluation_rows):
  """
      Send email with a link to confirm evaluations.
  """
  sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))

  to_email = mail.Email(email)
  from_email = mail.Email('CUNY_Tranfer_Reviews@provost-access-148820.appspotmail.com')
  subject = 'Link for confirming your reviews'
  suffix = 's'
  it_them = 'them'
  this_these = 'these'
  # Number of evaluations is 1 less than number of rows 'cause of header row.
  if evaluation_rows.count('</tr>') == 2:
    suffix = ''
    it_them = 'it'
    this_these = 'this'

  button_text = 'submit {} review{}'.format(this_these, suffix).title()
  html_body = mail.Content('text/html', """
  <p>
    Use the link below to confirm that you want to record the following transfer rule
    review{}.<br/>
    You may ignore this message if you did not perform {} review{} or if you have decided not
    to record {}.
  </p>
  {}
  <h2>
    <a  href="{}"
        style="font-weight: bold;
               font-variant:small-caps;
               padding:0.5em;
               font-size: 1em;">{}
    </a>
  </h2>
  <p>This link will expire in 48 hours.</p>
  """.format(suffix, this_these, suffix, it_them,
             evaluation_rows,
             url,
             button_text))
  message = mail.Mail(from_email, subject, to_email, html_body)
  response = sg.client.mail.send.post(request_body=message.get())
  return response
