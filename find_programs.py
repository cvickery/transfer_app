#! /usr/local/bin/python3
""" This is the algorithm for returning program info bsed on what the user has typed.
"""

import argparse
import psycopg
import sys

from collections import defaultdict
from psycopg.rows import namedtuple_row

ignore_words = set(('all', 'and', 'general', 'general.', 'or', 'other', 'other.', 'other,'))
# Cache plan and subplan tables w/ enrollments by CIP code
with psycopg.connect('dbname=cuny_curriculum') as conn:
  with conn.cursor(row_factory=namedtuple_row) as cursor:
    cursor.execute("""
    select p.institution, p.plan, p.plan_type, p.description, p.cip_code,
           coalesce(e.enrollment, 0) as enrollment
      from cuny_acad_plan_tbl p left join cuny_acad_plan_enrollments e
        on p.institution = e.institution
       and p.plan = e.plan
    """)
    plans = defaultdict(list)
    cip_soc_words = defaultdict(str)
    for row in cursor.fetchall():
      plans[row.cip_code].append((row.institution, row.plan, row.enrollment))
    # for k, v in plans.items():
    #   print(k, len(v), file=sys.stderr)
    cursor.execute("""
    select cip2020code, cip2020title, soc2018title
      from cip_soc
     where cip2020code !~* '^9'
    """)
    for row in cursor.fetchall():
      cip_code = row.cip2020code
      cip_words = tuple(row.cip2020title
                        .lower()
                        .replace('program.', '')
                        .replace('program,', '')
                        .replace('programs', '')
                        .replace(',', '')
                        .split())
      cip_set = set(cip_words)
      soc_words = tuple(row.soc2018title.lower().split())
      soc_set = set(soc_words)
      words_set = cip_set.union(soc_set).difference(ignore_words)
      cip_soc_words[cip_code] = ' '.join(words_set)


def find_programs(search_request: dict):
  """ See if we can return a list of cip_codes
  """
  assert isinstance(search_request, dict)
  colleges = [college.upper().strip('01') + '01' for college in search_request['colleges']]
  do_plans = search_request['plans']
  do_subplans = search_request['subplans']
  search_text = search_request['search_text']
  print(f'{colleges=} {do_plans=} {do_subplans=} {search_text=}')

  cip_codes = [k for k, v in cip_soc_words.items() if search_text in v]
  return_dict = {'cip_codes': cip_codes,
                 'coarse': {'plans': [], 'subplans': []},
                 'medium': {'plans': [], 'subplans': []},
                 'fine': {'plans': [], 'subplans': []}
                 }
  return return_dict


if __name__ == '__main__':
  parser = argparse.ArgumentParser('Interactive find_programs')
  parser.add_argument('-c', '--colleges', nargs='+', default=[])
  parser.add_argument('-p', '--plans', action='store_true')
  parser.add_argument('-s', '--subplans', action='store_true')
  parser.add_argument('search_text')
  args = parser.parse_args()

  do_plans = args.plans or not (args.plans or args.subplans)

  search_request = {'search_text': args.search_text,
                    'colleges': args.colleges,
                    'plans': do_plans,
                    'subplans': args.subplans
                    }

  print(find_programs(search_request))