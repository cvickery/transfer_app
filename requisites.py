#! /usr/local/bin/python3

import argparse
from collections import namedtuple

import psycopg2
from psycopg2.extras import NamedTupleCursor

from dgw_parser import dgw_parser

RequirementInfo = namedtuple('RequirementInfo',
                             'requirement_id block type block_value title '
                             'period_start, period_stop, requirement_text')

trans_dict = dict()
for c in range(13, 31):
  trans_dict[c] = None

trans_table = str.maketrans(trans_dict)

# Create dict of known colleges
colleges = dict()
course_conn = psycopg2.connect('dbname=cuny_courses')
course_cursor = course_conn.cursor(cursor_factory=NamedTupleCursor)
course_cursor.execute('select substr(lower(code),0,4) as code, name from institutions')
for row in course_cursor.fetchall():
  colleges[row.code] = row.name


def get_requirements_text(institution, b_type, b_value, period):
  """ Return the info about and text of a requirement block.
  """
  cursor.execute(f"""select requirement_id, institution, block_type, block_value, title,
                     period_start, period_stop, requirement_text
                     from requirement_blocks
                     where institution = %s
                       and block_type = %s
                       and block_value = %s
                       and period_stop = %s
                 """, (institution, b_type, b_value, period))
  if cursor.rowcount == 0:
    return None
  assert cursor.rowcount == 1, f'Found {cursor.rowcount} requirement blocks'
  row = cursor.fetchone()
  row.requirement_text = row.requirement_text\
                            .translate(trans_table)\
                            .strip('"')\
                            .replace('\\r', '\r')\
                            .replace('\\n', '\n') + '\n'
  return RequirementInfo(row)


if __name__ == '__main__':
  # Command line args
  parser = argparse.ArgumentParser(description='Test DGW Parser')
  parser.add_argument('-d', '--debug', action='store_true', default=False)
  parser.add_argument('-f', '--format')
  parser.add_argument('-i', '--institution', default='QNS01')
  parser.add_argument('-t', '--type', default='MAJOR')
  parser.add_argument('-v', '--value', default='CSCI-BS')

  # Parse args and handle default list of institutions
  args = parser.parse_args()
  digits = '0123456789'
  institution = f'{args.institution.lower().strip(digits)}'
  b_type = f'{args.type.upper()}'
  b_value = f'{args.value.upper()}'
  if args.debug:
    print(f'institution: {institution}')
    print(f'block type: {b_type}')
    print(f'block value: {b_value}')

  # Get the top-level requirements to examine: college, block-type, and/or block value
  conn = psycopg2.connect('dbname=cuny_programs')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)

  query = """
      select requirement_id, title, requirement_text
      from requirement_blocks
      where institution = %s
        and block_type = %s
        and block_value = %s
        and period_stop = '99999999'
      """
  cursor.execute(query, (institution, b_type, b_value))
  if cursor.rowcount == 0:
    print(f'No match for {institution} {b_type} {b_value}')
  else:
    for row in cursor.fetchall():
      if args.debug:
        print(f'{institution}, {type} {value} "{row.title}" '
              f'{len(row.requirement_text)} chars')
      requirement_text = row.requirement_text\
                            .translate(trans_table)\
                            .strip('"')\
                            .replace('\\r', '\r')\
                            .replace('\\n', '\n')
      print(dgw_parser(institution, requirement_text + '\n', type, value, row.title))
