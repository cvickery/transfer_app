#! /usr/local/bin/python3

import inspect
from pprint import pprint
from typing import List, Set, Dict, Tuple, Optional

import argparse
import sys
from io import StringIO


import psycopg2
from psycopg2.extras import NamedTupleCursor
from collections import namedtuple

from dgw_parser import dgw_parser

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


if __name__ == '__main__':

  # Command line args
  parser = argparse.ArgumentParser(description='Test DGW Parser')
  parser.add_argument('-d', '--debug', action='store_true', default=False)
  parser.add_argument('-f', '--format')
  parser.add_argument('-i', '--institutions', nargs='*', default=['QNS01'])
  parser.add_argument('-t', '--types', nargs='+', default=['MAJOR'])
  parser.add_argument('-v', '--values', nargs='+', default=['CSCI-BS'])
  parser.add_argument('-a', '--development', action='store_true', default=False)

  # Parse args and handle default list of institutions
  args = parser.parse_args()
  types = [f'{t.upper()}' for t in args.types]
  values = [f'{v.upper()}' for v in args.values]

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
  for institution in args.institutions:
    institution = institution.upper() + ('01' * (len(institution) == 3))
    for b_type in types:
      for b_value in values:
        if args.debug:
          print(institution, b_type, b_value)
        print(dgw_parser(institution, b_type, b_value))
