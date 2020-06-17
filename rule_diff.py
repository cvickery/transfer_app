#! /usr/local/bin/python3
""" Compare two rule archives at report changes
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

# An ArchiveSet consists of lists of source courses and destination courses, linked by a common
# rule_key.
ArchiveSet = namedtuple('ArchiveSet', 'destination_courses source_courses')
SourceCourses = namedtuple('SourceCourses', 'rule_key course_id offer_nbr '
                           ' min_credits max_credits credits_source min_gpa max_gpa')
DestinationCourses = namedtuple('DestinationCourses', 'rule_key course_id offer_nbr '
                                ' transfer_credits')

# Module initialization
# =================================================================================================
_archive_dir = os.getenv('ARCHIVE_DIR')
if _archive_dir is None:
  _archive_dir = '/Users/vickery/CUNY_Curriculum/rules_archive'

# Get available archive sets.
_archive_files = Path(_archive_dir).glob('*.bz2')
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
  available_archive_dates[key] = date.fromisoformat(key).strftime('%b %d, %Y')


# archive_dates()
# -------------------------------------------------------------------------------------------------
def archive_dates():
  """ Return dates of earliest and latest archives available.
  """
  first_date = date.fromisoformat(_all_archive_keys[0])
  last_date = date.fromisoformat(_all_archive_keys[-1])
  return (first_date.strftime('%b %d, %Y'), last_date.strftime('%b %d, %Y'))


# diff_rules()
# -------------------------------------------------------------------------------------------------
def diff_rules(first, second, debug=False):
  """ Diff rules from the archive. Default is the most recent two. Otherwise, use the last
      available archive before first and the most recent one since second.

      Return a dict keyed by rule with tuple of from-to course_id lists for the two archive dates
      used. Tuple is None for added/deleted rules.
  """
  if first is None:
    first = 'latest'
  if second is None:
    second = 'latest'
  first, second = (min(first, second), max(first, second))

  if first == 'latest':
    first_date = _all_archive_keys[-2]
  else:
    # Get latest date that is earlier than first
    _all_archive_keys.reverse()
    for first_date in _all_archive_keys:
      if first_date <= first:
        break
    _all_archive_keys.reverse()

  if second == 'latest':
    second_date = _all_archive_keys[-1]
  else:
    # Get earliest date that is later than second
    for second_date in _all_archive_keys:
      if second_date > second:
        break

  first_set = ArchiveSet._make(sorted(_all_archives[first_date]))
  second_set = ArchiveSet._make(sorted(_all_archives[second_date]))

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
      # if key == 'BAR01-LEH01-AAM-1':
      #   print(key, first_rules_source[key], second_rules_source[key],
      #         first_rules_destination[key], second_rules_destination[key], file=sys.stderr)
      first_rules_source[key].sort()
      second_rules_source[key].sort()
      first_rules_destination[key].sort()
      second_rules_destination[key].sort()
      if (first_rules_source[key] == second_rules_source[key]
         and first_rules_destination[key] == second_rules_destination[key]):
        # print(f'{key:<20}\t No Change')
        pass
      else:
        # print(f'{key:<20}\t Changed', end='')
        # print(f' from {first_rules_source[key]} => {first_rules_destination[key]}'
        #       f' to {second_rules_source[key]} => {second_rules_destination[key]}\n')
        result[key] = {first_date: (first_rules_source[key], first_rules_destination[key]),
                       second_date: (second_rules_source[key], second_rules_destination[key])}
    except KeyError as e:
      if key not in first_keys:
        # print(f'{key:<20}\t Added')
        result[key] = {first_date: None,
                       second_date: (second_rules_source[key], second_rules_destination[key])}
      elif key not in second_keys:
        # print(f'{key:<20}\t Deleted')
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
  parser.add_argument('-d', '--debug', action='store_true')
  parser.add_argument('dates', nargs='*')
  args = parser.parse_args()

  dates = args.dates
  while len(dates) < 2:
    dates += [None]
  first_date, second_date, result = diff_rules(dates[0], dates[1], debug=args.debug)
  print(first_date, second_date)
  for key, value in result.items():
    print(key, value)
