import os

from html2text import html2text
from sendgrid import SendGridAPIClient

""" This module sends email!

    For now, it uses the SendGrid API and the SendGrid credentials that I set up, and which works
    from any client, including when I am on a development machine that isn’t configured for sending
    email. But the production implementation could use the native Python library.
"""


class Struct:
    """ A structure that can have any fields defined. Allows dotted access to members without the
        constraints of namedtuples.
        Used only in this module, but should be moved to a more meaningful place if more widely
        adopted.
        Thank you to Peter Norvig. https://norvig.com/python-iaq.html
    """
    def __init__(self, **entries):
      self.__dict__.update(entries)


def send_message(to_list, from_addr, subject, html_msg, cc_list=None, bcc_list=None):
  """ Sent an email message using SendGrid.

      THIS IS THE CODE THAT HAS TO CHANGE if not using SendGrid.
  """
  assert os.environ.get('SENDGRID_API_KEY') is not None, 'Email not configured'
  sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
  assert type(to_list) is list
  assert type(from_addr) is dict
  assert type(subject) is str
  assert type(html_msg) is str

  """ The SendGrid message object must include personalizations, subject, from, and content fields.
      Personalizations is an array of recipients and subject lines.
      See https://sendgrid.com/docs/for-developers/sending-email/personalizations/ for rationale.
  """
  # Build a SendGrid message object from the function arguments.
  to_emails = [{'email': person['email'], 'name': person['name']} for person in to_list]
  sg_message = {'personalizations': [{'to': to_emails, 'subject': subject}],
                'from': from_addr,
                'content': [{'type': 'text/plain', 'value': html2text(html_msg)},
                            {'type': 'text/html', 'value': html_msg}]}
  if cc_list is not None:
    assert type(cc_list) is list
    sg_message['personalizations'][0]['cc'] = [{'email': person['email'],
                                                'name': person['name']} for person in cc_list]
  if bcc_list is not None:
    assert type(bcc_list) is list
    sg_message['personalizations'][0]['bcc'] = [{'email': person['email'],
                                                 'name': person['name']} for person in bcc_list]
  try:
    response = sg.send(sg_message)
  except Exception as error:
    return Struct(status_code='Failed', body=error)
  return response


def send_token(email, url, review_rows):
  """ Format a message with a link for confirming transfer rule evaluations, and email it to the
      reviewer.
  """

  # Format the message body and subject line, depending on how many rules were reviewed
  suffix = 's'
  it_them = 'them'
  this_these = 'these'
  # Number of reviews is 1 less than number of rows 'cause of header row.
  if review_rows.count('</tr>') == 2:
    suffix = ''
    it_them = 'it'
    this_these = 'this'
  subject_line = f'Confirming your transfer rule review{suffix}'
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
  return send_message(to_list=[{'email': email, 'name': ''}],
                      from_addr={'email': 'cvickery@qc.cuny.edu', 'name': 'CUNY Transfer App'},
                      subject=subject_line,
                      html_msg=html_body)
