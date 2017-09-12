from urllib.parse import urlparse

import smtplib

from email.message import EmailMessage
from email.headerregistry import Address

def send_token(token, url, email, evaluations='<tr><td>None</td></tr>'):
  """
      Send an email with a link to verfiy evaluations to someone.
  """
  parsed_url = urlparse(url)
  msg = EmailMessage()
  msg['Subject'] = 'This is your test message'
  msg['From'] = Address('Christopher Vickery', 'cvickery', 'qc.cuny.edu')
  msg['To'] = Address(addr_spec='{}'.format(email))

  msg.set_content('You need to view this message as HTML')
  msg.add_alternative("""
  <html>
    <head>
    </head>
    <body>
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
        Clicking the link below will open a confirmation page at
        {}.
      </h2>
        <a  href="{}?token={}"
            style="font-weight: bold;
                   font-variant:small-caps;
                   padding:0.5em;
                   font-size: 1.3em;"
                   border-radius=0.25em;>
          activate these evaluations
        </a>
    </body>
  </html>
  """.format(evaluations, parsed_url.netloc, parsed_url.geturl(), token), subtype="html")
  with smtplib.SMTP('localhost') as s:
    s.send_message(msg)
