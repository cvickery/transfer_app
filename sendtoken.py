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
  text_body = mail.Content('text/plain', 'You need to view this message as HTML')
  suffix = 's'
  if evaluation_rows.count('<tr>') == 1: suffix = ''
  html_body = mail.Content('text/html',"""
  <p>
    Use the button below to confirm that you have evaluated the following transfer rules and
    are ready to activate them.
    If you did not perform these evaluations or if you have decided not to have them recorded
    you may ignore this message.
  </p>
  <table style="border-collapse:collapse; border: 1px solid black;">
    {}
  </table>
  <h2>
    The link below will activate your evaluation{} and open a confirmation page at {}.
  </h2>
  <a  href="{}"
      style="font-weight: bold;
             font-variant:small-caps;
             padding:0.5em;
             font-size: 1.3em;"
             border-radius=0.25em;>
    activate evaluation{}
  </a>
  """.format(evaluation_rows,
             suffix,
             parsed_url.netloc.replace('.', '․'),
             parsed_url.geturl(),
             suffix))
  message = mail.Mail(from_email, subject, to_email, html_body)
  response = sg.client.mail.send.post(request_body=message.get())
  return response