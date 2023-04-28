#! /usr/local/bin/python3
import argparse
import os
import re
import sys

from html2text import html2text
from sendgrid import SendGridAPIClient
from socket import gethostname

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


# **************** THIS IS THE CODE THAT HAS TO CHANGE IF NOT USING SENDGRID ***********************
def send_message(to_list, from_addr, subject, html_msg,
                 text_msg=None, cc_list=None, bcc_list=None, reply_addr=None):
  """ Sent an email message using SendGrid.
  """
  assert os.environ.get('SENDGRID_API_KEY') is not None, 'Email not configured'
  sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
  assert type(to_list) is list, f'send_message: to_list ({to_list}) is not a list'
  assert type(from_addr) is dict, f'send_message: from_addr ({from_addr}) is not a dict'
  assert type(subject) is str, f'send_message: subject ({subject}) is not a string'
  assert type(html_msg) is str, f'send_message: html_msg ({html_msg}) is not a string'
  """ The SendGrid message object must include personalizations, subject, from, and content fields.
      Personalizations is an array of recipients and subject lines.
      See https://sendgrid.com/docs/for-developers/sending-email/personalizations/ for rationale.
  """
  # Plain text is optional: generate it if not provided
  if text_msg is None:
    text_msg = html2text(html_msg)

  # Build a SendGrid message object from the function arguments.
  # Apparently, SendGrid chokes if the same email address appears more than once in the To, Cc, or
  # Bcc lists, so first analyze those lists and remove duplicates.
  unique_set = set()
  for person in to_list:
    if person['email'].lower() in unique_set:
      to_emails.remove(person)
    else:
      unique_set.add(person['email'].lower())
  sg_message = {'personalizations': [{'to': to_list, 'subject': subject}],
                'from': from_addr,
                'content': [{'type': 'text/plain', 'value': text_msg},
                            {'type': 'text/html', 'value': html_msg}]}
  if reply_addr is not None:
    sg_message['reply_to'] = reply_addr
  if cc_list is not None:
    for person in cc_list:
      if person['email'].lower() in unique_set:
        cc_list.remove(person)
      else:
        unique_set.add(person['email'].lower())
    if len(cc_list) > 0:
      sg_message['personalizations'][0]['cc'] = [{'email': person['email'],
                                                  'name': person['name']} for person in cc_list]
  if bcc_list is not None:
    for person in bcc_list:
      if person['email'].lower() in unique_set:
        bcc_list.remove(person)
      else:
        unique_set.add(person['email'].lower())
    if len(bcc_list) > 0:
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
  button_text = f'activate {this_these} review{suffix}'.title()
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


# Command Line Interface
# =================================================================================================

class ParseError(Exception):
  """Malformed email addresses raise this one.
  """
  def __init__(self, expression, message):
    self.expression = expression
    self.message = message

  def __str__(self):
    return f'{self.__class__.__name__}: {self.expression}: {self.message}'


def parse_addr_str(str, strict=False):
  """ Extract display_name, username and domain from a string.
      Return a dict with email and name fields.
      If str is malformed, raise ParseError if strict; otherwise return None
  """
  m = re.search(r'^\s*(<.+>)?\s*(\S+)@(\S+)\s*$', str)
  if m is None:
    if strict:
      raise ParseError(str, 'invalid email string')
    return None
  email = f'{m[2]}@{m[3]}'
  if m[1] is None:
    return {'email': email, 'name': email.title().replace('.', ' ')}
  else:
    return {'email': email, 'name': m[1].strip('> <')}


if __name__ == '__main__':
  """ Use the same arguments as mail.py, but send using the mail service (SendGrid) implemented
      above.
  """
  parser = argparse.ArgumentParser(description='Commandline interface to sendmail.py',
                                   add_help=False)
  parser.add_argument('-?', '--help', action='help')
  parser.add_argument('-s', '--subject', default='Test Message')
  parser.add_argument('-c', '--cc_addr', nargs='+')
  parser.add_argument('-b', '--bcc_addr', nargs='+')
  parser.add_argument('-r', '--reply_addr')
  parser.add_argument('-h', '--html_file', type=argparse.FileType('r'))
  parser.add_argument('-t', '--text_file', type=argparse.FileType('r'))
  parser.add_argument('-d', '--debug', type=int, default=0)
  parser.add_argument('-f', '--from_addr',
                      default=f"<{os.getenv('USER')}> {os.getenv('USER')}@{gethostname()}")
  parser.add_argument('to_addr', nargs='+')
  args = parser.parse_args()

  # Prefix for error reporting
  whoami = f'{parser.prog} error:'

  # Be sure sender and all recipients are valid
  try:

    from_addr = parse_addr_str(args.from_addr, strict=True)
    if from_addr is None:
      exit(f'{whoami} “{args.from_addr}” is not a valid return address')

    if args.reply_addr is not None:
      reply_addr = parse_addr_str(args.reply_addr, strict=True)
    else:
      reply_addr = None
    to_list = [parse_addr_str(person, strict=True) for person in args.to_addr]

    if args.cc_addr is None:
      cc_list = None
    else:
      cc_list = [parse_addr_str(person) for person in args.cc_addr]

    if args.bcc_addr is None:
      bcc_list = None
    else:
      bcc_list = [parse_addr_str(person) for person in args.bcc_addr]

  except ParseError as err:
    print(err)
    exit(1)

  # Read plain text body from stdin if no files specified
  if args.html_file is None and args.text_file is None:
    text_body = ''
    for line in sys.stdin:
      text_body += line

  # Plain text part
  if args.text_file is not None:
    text_body = args.text_file.read()

  # HTML part
  if args.html_file is not None:
    html_body = args.html_file.read()
  else:
    html_body = f'<pre>{text_body}</pre>'

  # Send the message
  try:
    send_message(to_list,
                 from_addr,
                 args.subject,
                 html_body,
                 text_body,
                 cc_list,
                 bcc_list,
                 reply_addr)
  except Exception as e:
    exit(f'{whoami} sending failed: {e}')

  exit(0)
