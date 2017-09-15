from urllib.parse import urlparse
from flask_mail import Message

def send_token(mail, email, url, evaluation_rows='<tr><td>None</td></tr>'):
  """
      Send email with a link to confirm evaluations.
  """
  parsed_url = urlparse(url)

  msg = Message(subject='Link for confirming your evaluations', recipients=[email])

  msg.body = 'You need to view this message as HTML'
  msg.html = """
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
  <a  href="{}"
      style="font-weight: bold;
             font-variant:small-caps;
             padding:0.5em;
             font-size: 1.3em;"
             border-radius=0.25em;>
    activate these evaluations
  </a>
  """.format(evaluation_rows, parsed_url.netloc, parsed_url.geturl())
  mail.send(msg)
