#! /usr/local/bin/python3
""" This is the algorithm for returning program info bsed on what the user has typed.
"""

import argparse
import psycopg
import re

from collections import defaultdict
from nltk.stem import SnowballStemmer
from psycopg.rows import namedtuple_row

stemmer = SnowballStemmer('english')

# Ignore “short” words and longer words that appear in CIP/SOC titles but don't add meaning.
min_word_length = 4   # characters
ignore_words = set(('general', 'match', 'other'))

# Replace punctuation from CIP/SOC titles and search_text strings with spaces to make word
# extraction better.
punctuation = ['.', ',', ';', ':', '/', '&']
punctuation_re = f"[{' '.join(punctuation)}]"

# Drop hyphens for better matches (Pre-Med == premed, etc.)
elide_re = r'[\-]'

# Build the dictionaries used by find_programs()
# =================================================================================================

# Plans and their enrollments
with psycopg.connect('dbname=cuny_curriculum') as conn:
  with conn.cursor(row_factory=namedtuple_row) as cursor:
    # Cache plan and subplan tables w/ enrollments by CIP code
    cursor.execute("""
    select p.institution, p.plan, p.plan_type, p.description, p.cip_code,
           coalesce(e.enrollment, 0) as enrollment,
           r.block_type, r.block_value, r.title
      from cuny_acad_plan_tbl p
              left join cuny_acad_plan_enrollments e
                on p.institution = e.institution
                and p.plan = e.plan
              left join requirement_blocks r
                on r.institution = p.institution
                and r.block_value = p.plan
                and r.period_stop ~* '^9'
      where p.plan !~* '^mhc'
    """)
    plans = defaultdict(set)

    for row in cursor.fetchall():
      if row.title is None:
        # DGW lookup failed
        # print(row.institution, row.plan, row.enrollment, 'No DAP_REQ_BLOCK')
        plans[row.cip_code].add((row.institution, row.plan, row.enrollment, row.description))
      else:
        plans[row.cip_code].add((row.institution, row.plan, row.enrollment, row.title))

    # Every "meaningful" word that appears in a CIP or SOC title.
    all_cip_soc_words = set()

    # String of search words from cip-soc for each cip code
    cip_soc_strings = defaultdict(str)
    cursor.execute("""
    select cip2020code, cip2020title, soc2018title
      from cip_soc
     where cip2020code !~* '^9' -- 99.9999, etc mean "no match"
    """)
    for row in cursor.fetchall():
      cip_code = row.cip2020code
      cip_string = re.sub(elide_re, '', re.sub(punctuation_re, ' ', row.cip2020title))
      cip_words = tuple(stemmer.stem(word) for word in cip_string.lower().split()
                        if len(word) >= min_word_length)
      cip_set = set(cip_words)
      soc_string = re.sub(elide_re, '', re.sub(punctuation_re, ' ', row.soc2018title))
      soc_words = tuple(stemmer.stem(word) for word in soc_string.lower().split()
                        if len(word) >= min_word_length)
      soc_set = set(soc_words)
      words_set = cip_set.union(soc_set).difference(ignore_words)
      cip_soc_strings[cip_code] = ' '.join(words_set)

      all_cip_soc_words = all_cip_soc_words.union(words_set)

    # Convert to a string so that search word prefixes will find matches
    all_cip_soc_words = ' '.join(all_cip_soc_words)

    # Cache the names of the coarse, medium, and fine CIP codes (i.e., all of them: the cip2020codes
    # table is already organized with separate 2, 4, and 6 digit codes)
    cursor.execute("""
    select cip_code, cip_title
      from cip2020codes
    """)
    cip_code_titles = {row.cip_code: row.cip_title for row in cursor.fetchall()}


def find_programs(search_request: dict):
  """ Return coarse, medium, and fine lists of cip_code tuples (code, title) and plan tuples
      (institution, plan, enrollment, title)
  """
  assert isinstance(search_request, dict)

  # Extract info about what to find from the search_request dict
  search_text = search_request['search_text']
  try:
    large_enough = float(search_request['enough'])
  except (KeyError, ValueError):
    large_enough = 0.5

  # Extract search_words from the search string
  search_words = set()
  for word in re.sub(elide_re, '', re.sub(punctuation_re, ' ', search_text.lower())).split():
    if len(word) >= min_word_length and stemmer.stem(word) in all_cip_soc_words:
      search_words.add(stemmer.stem(word))
  num_search_words = len(search_words)

  # Select cip_codes where the portion of search_words appearing in cip_soc_words is “large enough.”
  # These are full six-digit CIP codes
  cip_codes = set()

  for cip_code, cip_soc_str in cip_soc_strings.items():

    num_matches = 0
    for search_word in search_words:
      if search_word in cip_soc_str:
        num_matches += 1

    if (large_enough == 0.0
       or (num_search_words > 0 and ((num_matches / num_search_words) >= large_enough))):
      cip_codes.add(cip_code)

  # Now get the tripartite CIP and plan info for each cip_code.
  coarse_cip_set = set()
  medium_cip_set = set()
  fine_cip_set = set()

  coarse_plan_set = set()
  medium_plan_set = set()
  fine_plan_set = set()

  for cip_code in cip_codes:
    cip_coarse = cip_code[0:2]
    cip_medium = cip_code[0:5]
    cip_fine = cip_code[0:7]

    coarse_cip_set.add(f'{cip_coarse}: {cip_code_titles[cip_coarse]}')
    medium_cip_set.add(f'{cip_medium}: {cip_code_titles[cip_medium]}')
    fine_cip_set.add(f'{cip_fine}: {cip_code_titles[cip_fine]}')

    # Since we are looking for partial key matches, there's no choice but to go through all the
    # plans for all each the matching CIP codes
    for k, v in plans.items():
      if k[0:2] == cip_coarse:
        coarse_plan_set = coarse_plan_set.union(v)
      if k[0:5] == cip_medium:
        medium_plan_set = medium_plan_set.union(v)
      if k[0:7] == cip_fine:
        fine_plan_set = fine_plan_set.union(v)

  # Sort each plan set by decreasing enrollment size
  for v in coarse_plan_set:
    coarse_plan_set = sorted(coarse_plan_set, key=lambda item: item[2], reverse=True)
    medium_plan_set = sorted(medium_plan_set, key=lambda item: item[2], reverse=True)
    fine_plan_set = sorted(fine_plan_set, key=lambda item: item[2], reverse=True)

  return_dict = {'coarse': {'cip_codes': list(sorted(coarse_cip_set)),
                            'plans': list(coarse_plan_set)},
                 'medium': {'cip_codes': list(sorted(medium_cip_set)),
                            'plans': list(medium_plan_set)},
                 'fine': {'cip_codes': list(sorted(fine_cip_set)),
                          'plans': list(fine_plan_set)}
                 }

  return return_dict


if __name__ == '__main__':
  parser = argparse.ArgumentParser('Interactive find_programs')
  parser.add_argument('-c', '--colleges', nargs='+', default=[])
  parser.add_argument('-e', '--enough', type=float, default=0.5)
  parser.add_argument('-p', '--plans', action='store_true')
  parser.add_argument('-s', '--subplans', action='store_true')
  parser.add_argument('search_text')
  args = parser.parse_args()

  do_plans = args.plans or not (args.plans or args.subplans)

  search_request = {'search_text': args.search_text,
                    'colleges': args.colleges,
                    'plans': do_plans,
                    'subplans': args.subplans,
                    'enough': args.enough
                    }

  search_result = find_programs(search_request)
  for k, v in search_result.items():
    print(f'{k.upper()}: {len(v["cip_codes"])=} {len(v["plans"])=}')
    for index, item in enumerate(v["cip_codes"]):
      print(index, item)

    for index, item in enumerate(v["plans"]):
      print(index, item)
