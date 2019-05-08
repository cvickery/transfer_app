import os
from sendgrid import SendGridAPIClient


class Struct:
    """ A structure that can have any fields defined.
        Thank you: Peter Norvig. https://norvig.com/python-iaq.html
    """
    def __init__(self, **entries):
      self.__dict__.update(entries)


def send_token(email, url, review_rows):
  """ Use SendGrid to send email with a link for confirming transfer rule evaluations.
  """
  assert os.environ.get('SENDGRID_API_KEY') is not None, 'Email not configured'
  sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))

  # Format the message body, depending on how many rules were reviewed
  suffix = 's'
  it_them = 'them'
  this_these = 'these'
  # Number of reviews is 1 less than number of rows 'cause of header row.
  if review_rows.count('</tr>') == 2:
    suffix = ''
    it_them = 'it'
    this_these = 'this'

  button_text = 'submit {} review{}'.format(this_these, suffix).title()
  html_body = f"""
  <p>
    Use the link below to confirm that you want to record the following transfer rule
    review{suffix}.<br/>
    You may ignore this message if you did not perform {this_these} review{suffix} or if you have
    decided not to record {it_them}.
  </p>
  {review_rows}
  <h2>
    <a  href="{url}"
        style="font-weight: bold;
               font-variant:small-caps;
               padding:0.5em;
               font-size: 1em;">{button_text}
    </a>
  </h2>
  <p>This link will expire in 48 hours.</p>
  """
  message = {'personalizations': [{'to': [{'email': email}],
             'subject': 'Confirming your transfer rule review{suffix}'}],
             'from': {'email': 'poffice@qc.cuny.edu',
                      'name': 'CUNY Transfer App'},
             'content': [{'type': 'text/html',
                          'value': html_body}]
             }
  try:
    response = sg.send(message)
  except Exception as error:
    return Struct(status_code='Failed', body=error)
  return response
