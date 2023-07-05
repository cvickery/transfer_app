#! /usr/local/bin/python3
"""Compare two rule archives and report changes.

The default is to compare the two latest archive sets.
"""

import os
import bz2
import csv
import sys
from argparse import ArgumentParser
from collections import defaultdict, namedtuple
from datetime import date
from pathlib import Path
from pgconnection import PgConnection

# An ArchiveSet consists of lists of source courses and destination courses, linked by a common
# rule_key.
ArchiveSet = namedtuple('ArchiveSet', 'destination_courses effective_dates source_courses')
SourceCourses = namedtuple('SourceCourses', 'rule_key course_id offer_nbr '
                           ' min_credits max_credits credits_source min_gpa max_gpa')
DestinationCourses = namedtuple('DestinationCourses', 'rule_key course_id offer_nbr '
                                ' transfer_credits')
EffectiveDates = namedtuple('EffectiveDates', 'rule_key, effective_date')

# Module initialization
# =================================================================================================
_archive_dir = os.getenv('ARCHIVE_DIR')
if _archive_dir is None:
  home_dir = Path.home()
  _archive_dir = Path(home_dir, 'Projects/cuny_curriculum/rules_archive')

# Get available archive sets.
_archive_files = _archive_dir.glob('*.bz2')
_all_archives = defaultdict(list)
for archive_file in _archive_files:
  archive_date = archive_file.name[0:10]
  _all_archives[archive_date].append(archive_file)
if len(_all_archives) < 2:
  raise ValueError(f'Not enough archive sets available. {len(_all_archives)} found.')

# Put the keys in order
_all_archive_keys = list(_all_archives.keys())
_all_archive_keys.sort()

# Provide public list of available archive_dates
available_archive_dates = dict()
for key in _all_archive_keys:
  available_archive_dates[key] = date.fromisoformat(key).strftime('%B %-d, %Y')


# is_bkcr()
# -------------------------------------------------------------------------------------------------
def is_bkcr(course_id):
  """Look up the course to see if it has the BKCR attribute."""
  course_id = int(course_id)
  conn = PgConnection()
  cursor = conn.cursor()
  cursor.execute(f"""
select * from cuny_courses
 where course_id = {course_id}
   and attributes ~* 'BKCR'
   """)
  assert cursor.rowcount < 2
  rowcount = cursor.rowcount
  conn.close()

  return rowcount > 0


# archive_dates()
# -------------------------------------------------------------------------------------------------
def archive_dates():
  """Return dates of earliest and latest archives available."""
  first_date = date.fromisoformat(_all_archive_keys[0])
  last_date = date.fromisoformat(_all_archive_keys[-1])
  return (first_date.strftime('%b %d, %Y'), last_date.strftime('%B %-d, %Y'))


# diff_rules()
# -------------------------------------------------------------------------------------------------
def diff_rules(first, second, debug=False, rogues=False):
  """Diff rules from the archive.

  Default is the most recent two. Otherwise, use the last available archive before first and the
  most recent one since second.

  Return a dict keyed by rule with tuple of from-to course_id lists for the two archive dates used.
  Tuple is None for added/deleted rules.
  """
  # Missing dates default to two most recent ones
  if first is None or first == 'latest':
    first_date = _all_archive_keys[-2]
  else:
    first_date = first
  if second is None or second == 'latest':
    second_date = _all_archive_keys[-1]
  else:
    second_date = second

  # Display results in date order even if entered backwards
  first_date, second_date = (min(first_date, second_date), max(first_date, second_date))

  # Short-circuit if user asks for the same dates
  if first_date == second_date:
    return first_date, second_date, dict()

  # Find the last archive dates that are before or equal to the ones selected.
  first_target = first_date
  second_target = second_date
  for archive_date in _all_archive_keys:
    if archive_date <= first_target:
      first_date = archive_date
    if archive_date <= second_target:
      second_date = archive_date

  if debug:
    print(f'Asked for {first_target} and {second_target}. Using {first_date} and {second_date}')
  # Put archive files in alphabetic order: destination -> effective_date -> source
  _all_archives[first_date].sort()
  _all_archives[second_date].sort()

  first_set = ArchiveSet._make(_all_archives[first_date])
  second_set = ArchiveSet._make(_all_archives[second_date])

  if debug:
    print(f'Asked for {first}, {second}. Using {first_date}, {second_date}.', file=sys.stderr)

  # The CSV files have a separate row for each course that is part of a rule.
  # Here, we build four dictionaries, keyed by the rule_keys, containing lists of course_ids
  first_rules_source = dict()
  first_rules_destination = dict()

  if debug:
    print(f'{first_date} source ........ ', file=sys.stderr, end='')
  with bz2.open(first_set.source_courses, mode='rt') as csv_file:
    reader = csv.reader(csv_file)
    for line in reader:
      row = SourceCourses._make(line)
      if row.rule_key not in first_rules_source:
        first_rules_source[row.rule_key] = []
      first_rules_source[row.rule_key].append(row.course_id)
  if debug:
    print(f'{len(first_rules_source):,} rows', file=sys.stderr)

  if debug:
    print(f'{first_date} destination ... ', file=sys.stderr, end='')
  with bz2.open(first_set.destination_courses, mode='rt') as csv_file:
    reader = csv.reader(csv_file)
    for line in reader:
      row = DestinationCourses._make(line)
      if row.rule_key not in first_rules_destination:
        first_rules_destination[row.rule_key] = []
      first_rules_destination[row.rule_key].append(row.course_id)
  if debug:
    print(f'{len(first_rules_destination):,} rows', file=sys.stderr)

  second_rules_source = dict()
  second_rules_destination = dict()

  if debug:
    print(f'{second_date} source ........ ', file=sys.stderr, end='')
  with bz2.open(second_set.source_courses, mode='rt') as csv_file:
    reader = csv.reader(csv_file)
    for line in reader:
      row = SourceCourses._make(line)
      if row.rule_key not in second_rules_source:
        second_rules_source[row.rule_key] = []
      second_rules_source[row.rule_key].append(row.course_id)
  if debug:
    print(f'{len(second_rules_source):,} rows', file=sys.stderr)

  if debug:
    print(f'{second_date} destination ... ', file=sys.stderr, end='')
  with bz2.open(second_set.destination_courses, mode='rt') as csv_file:
    reader = csv.reader(csv_file)
    for line in reader:
      row = DestinationCourses._make(line)
      if row.rule_key not in second_rules_destination:
        second_rules_destination[row.rule_key] = []
      second_rules_destination[row.rule_key].append(row.course_id)
  if debug:
    print(f'{len(second_rules_destination):,} rows', file=sys.stderr)

  # The source and destination keys must match within the two sets
  first_keys = set(first_rules_source.keys())
  second_keys = set(second_rules_source.keys())
  assert first_keys == set(first_rules_destination.keys())
  assert second_keys == set(second_rules_destination.keys())

  # Work with the union of the two sets of rules
  all_archive_keys = first_keys | second_keys
  if debug:
    print(f'{len(first_keys):,} {first_date} rules and {len(second_keys):,} {second_date} rules '
          f'=>  {len(all_archive_keys):,} rules to check', file=sys.stderr)

  result = dict()
  for key in all_archive_keys:
    try:
      first_rules_source[key].sort()
      second_rules_source[key].sort()
      first_rules_destination[key].sort()
      second_rules_destination[key].sort()
      if (first_rules_source[key] == second_rules_source[key]
         and first_rules_destination[key] == second_rules_destination[key]):
        pass
      else:
        result[key] = {first_date: (first_rules_source[key], first_rules_destination[key]),
                       second_date: (second_rules_source[key], second_rules_destination[key])}
        if rogues:
          # Rogue detector: if new rule is one course and it's blanket credit, report it to the
          # proper authorities.
          if len(first_rules_destination[key]) == 1 and \
             len(second_rules_destination[key]) == 1 and \
             not is_bkcr(first_rules_destination[key][0]) and\
             is_bkcr(second_rules_destination[key][0]):
            print(f'{key} has gone rogue')

    except KeyError as e:
      if key not in first_keys:
        result[key] = {first_date: None,
                       second_date: (second_rules_source[key], second_rules_destination[key])}
      elif key not in second_keys:
        result[key] = {first_date: (first_rules_source[key], first_rules_destination[key]),
                       second_date: None}
      else:
        raise KeyError(f'{key:<20}\t Unexpected KeyError')
  return first_date, second_date, result


""" Module Test
"""
if __name__ == '__main__':

  # Command line options
  parser = ArgumentParser('Compare two rule archives')
  parser.add_argument('-c', '--count_only', action='store_true')
  parser.add_argument('-d', '--debug', action='store_true')
  parser.add_argument('-r', '--rogues', action='store_true')
  parser.add_argument('dates', nargs='*')
  args = parser.parse_args()

  dates = args.dates
  while len(dates) < 2:
    dates += [None]

  if args.debug:
    print(dates[0], dates[1])

  first_date, second_date, result = diff_rules(dates[0],
                                               dates[1],
                                               debug=args.debug,
                                               rogues=args.rogues)

  if args.count_only:
    print(f'There were {len(result)} rule changes between {first_date} and {second_date}')
  else:
    for key, value in result.items():
      print(key, value)
