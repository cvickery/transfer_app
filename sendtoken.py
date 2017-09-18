import os
from urllib.parse import urlparse
import sendgrid
from sendgrid.helpers import mail

def send_token(email, url, evaluation_rows='<tr><td>None</td></tr>'):
  """
      Send email with a link to confirm evaluations.
  """
  sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))
  parsed_url = urlparse(url)

  to_email = mail.Email(email)
  from_email = mail.Email('Tranfer.Evaluations@provost-access-148820.appspotmail.com')
  subject = 'Link for confirming your evaluations'
  suffix = 's'
  pronoun = 'them'
  if evaluation_rows.count('<tr>') == 1:
    suffix = ''
    pronoun = 'it'
  html_body = mail.Content('text/html',"""
  <p>
    Use the link below to confirm that you have evaluated the following transfer rule{} and
    are ready to activate {}.<br/>
    You may ignore this message if you did not perform these evaluations or if you have decided not to have them recorded.
  </p>
  <table style="border-collapse:collapse; border: 1px solid black;">
    {}
  </table>
  <h2>
    <a  href="{}"
        style="font-weight: bold;
               font-variant:small-caps;
               padding:0.5em;
               font-size: 1.3em;"
               border-radius=0.25em;>{}
    </a>
  </h2>
  <p>This link will be expire in 48 hours.</p>
  """.format(evaluation_rows,
             suffix, pronoun,
             parsed_url.geturl()))
  message = mail.Mail(from_email, subject, to_email, html_body)
  response = sg.client.mail.send.post(request_body=message.get())
  return response
