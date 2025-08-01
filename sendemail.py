#! /usr/local/bin/python3
""" This is sendemail.py modified to use smtplib instead of SendGrid.
"""
import argparse
import getpass
import os
import smtplib
import socket
import sys

from datetime import datetime
from email.message import EmailMessage
from html2text import html2text


# send_email()
# -------------------------------------------------------------------------------------------------
def send_email(from_addr, to_addrs, subject, html_body, text_body,
               cc_addrs=[], bcc_addrs=[], reply_to=None):
  """Populate an EmailMessage object from the given parameters, and send it via smtp.
  """
  msg = EmailMessage()
  # Required headers
  msg['From'] = f'{from_addr} <chris@christophervickery.com>'
  msg['To'] = ', '.join(to_addrs)
  msg['Subject'] = subject
  msg.set_content(text_body)
  msg.add_alternative(html_body, subtype='html')

  # Optional headers
  msg['Cc'] = ', '.join(cc_addrs)
  if reply_to:
    msg['Reply-To'] = reply_to

  # ChatGPT claims that all users might see the Bcc header, so it should not be set. (In practice,
  # the mailing systems I use seem to hide this header from users.)
  # if bcc_addrs:
  #   msg['Bcc'] = ', '.join(bcc_addrs)

  # Default smtp server is Dreamhost, where chris@christophervickery.com is a valid user.
  smtp_host = os.environ.get("SMTP_HOST", "smtp.dreamhost.com")
  smtp_port = int(os.environ.get("SMTP_PORT", 587))
  smtp_user = os.environ.get("SMTP_USER")
  smtp_pass = os.environ.get("SMTP_PASSWORD")

  with smtplib.SMTP(smtp_host, smtp_port) as s:
    s.starttls()
    s.login(smtp_user, smtp_pass)
    recipients = to_addrs + cc_addrs + bcc_addrs  # This is the list smtp uses for delivery.
    s.send_message(msg, to_addrs=recipients)
    print(f'Sent via {smtp_host}')


# __main__
# -------------------------------------------------------------------------------------------------
if __name__ == "__main__":
  # Info about the actual sender
  user = getpass.getuser()
  hostname = socket.gethostname()

  # Command line args: a subset of the Unix mail command options
  parser = argparse.ArgumentParser(description='Commandline interface to sendemail.py',
                                   add_help=False)
  parser.add_argument('-?', '--help', action='help')
  parser.add_argument('-s', '--subject',
                      default=f'Test Message {datetime.now().strftime("%Y-%m-%d %H:%M")}')
  parser.add_argument('-c', '--cc_addrs', nargs='+', default=[])
  parser.add_argument('-b', '--bcc_addrs', nargs='+', default=[])
  parser.add_argument('-r', '--reply_addr', default=None)
  parser.add_argument('-h', '--html_file', type=argparse.FileType('r'))
  parser.add_argument('-t', '--text_file', type=argparse.FileType('r'))
  parser.add_argument('-d', '--debug', action='store_true')
  parser.add_argument('-f', '--from_addr', default=f'{user} ({hostname})')
  parser.add_argument('to_addrs', nargs='+')
  args = parser.parse_args()

  """ Always send both text and html versions of the message body. Text can come from a file,
      stdin, or by converting html to Markdown. Html can come from a file or by wrapping the
      text in a <pre> element.
  """
  text_body = html_body = None

  # Read plain text body from stdin if no files specified
  if args.html_file is None and args.text_file is None:
    text_body = ''
    for line in sys.stdin:
      text_body += line
    if not text_body:
      # Allow this: the subject line may be all that’s needed.
      ...

  # Text from file?
  if args.text_file:
    text_body = args.text_file.read()

  # HTML from file?
  if args.html_file:
    html_body = args.html_file.read()

  if text_body and not html_body:
    html_body = f'<pre>{text_body}</pre>'
  if html_body and not text_body:
    text_body = html2text(html_body)

  if args.debug:
    print(f'{args.from_addr=}')
    print(f'{args.to_addrs=}')
    print(f'{args.subject=}')
    print(f'{html_body=}')
    print(f'{text_body=}')
    print(f'{args.cc_addrs=}')
    print(f'{args.bcc_addrs=}')
    print(f'{args.reply_addr=}')
    exit('*** END DEBUG ***')

  # Send the message
  try:
    send_email(args.from_addr,
               args.to_addrs,
               args.subject,
               html_body,
               text_body,
               args.cc_addrs,
               args.bcc_addrs,
               args.reply_addr)
  except Exception as e:
    exit(f'Sending failed: {e}')

  exit(0)
