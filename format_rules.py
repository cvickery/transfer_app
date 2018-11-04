
from collections import namedtuple
import json
import re
import argparse

from course_lookup import lookup_course
from pgconnection import pgconnection
from status_utils import status_string
from copy import copy

DEBUG = False

letters = ['F', 'F', 'D-', 'D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+']
Work_Tuple = namedtuple('Work_Tuple', 'course_id offer_nbr discipline')

# Named tuples for a transfer rule and its source and destination course lists.
Transfer_Rule = namedtuple('Transfer_Rule', """
                           rule_id
                           source_institution
                           destination_institution
                           subject_area
                           group_number
                           source_disciplines
                           source_subjects
                           review_status
                           source_courses
                           destination_courses
                           """)

# The information from the source and destination courses tables is augmented with a count of how
# many offer_nbr values there are for the course_id.
Source_Course = namedtuple('Source_Course', """
                           course_id
                           offer_count
                           discipline
                           catalog_number
                           cat_num
                           cuny_subject
                           min_credits
                           max_credits
                           min_gpa
                           max_gpa
                           """)

Destination_Course = namedtuple('Destination_Course', """
                                course_id
                                offer_count
                                discipline
                                catalog_number
                                cat_num
                                cuny_subject
                                transfer_credits
                                """)

conn = pgconnection('dbname=cuny_courses')
cursor = conn.cursor()
cursor.execute("select code, prompt from institutions order by lower(name)")
institution_names = {row.code: row.prompt for row in cursor}
cursor.execute('select * from transfer_rules')
rule_ids = dict()
for rule in cursor.fetchall():
  rule_ids['{}-{}-{}-{}'.format(rule.source_institution,
                                rule.destination_institution,
                                rule.subject_area,
                                rule.group_number)] = rule.id
conn.close()


# andor_list()
# -------------------------------------------------------------------------------------------------
def andor_list(items, andor='and'):
  """ Join a list of stings into a comma-separated con/disjunction.
      Forms:
        a             a
        a and b       a or b
        a, b, and c   a, b, or c
  """
  if len(items) == 1:
    return items[0]
  if len(items) == 2:
    return items[0] + f' {andor} ' + items[1]
  last_item = items.pop()
  return ', '.join(items) + f', {andor} ' + last_item


# numeric_part()
# -------------------------------------------------------------------------------------------------
def numeric_part(catalog_number):
  """ Helper function for format_rule and /_find_course_ids() AJAX utility.
      Returns the numeric part of a catalog_number (ignoring letter suffixes, etc) as a real number.
  """
  # ASSUMPTION: Catalog numbers are always less than 1,000. If larger, they are adjustments to
  # the "no decimals in catalog numbers" edict, so reduce them to the correct range.
  #
  # NOTE: this function has been added to the db so queries can select the return value from there.

  match = re.search(r'(\d+\.?\d*)', catalog_number)
  numeric_part = float(match.group(1))
  while numeric_part > 1000.0:
    numeric_part = numeric_part / 10.0
  return numeric_part


# _grade()
# -------------------------------------------------------------------------------------------------
def _grade(min_gpa, max_gpa):
  """ Convert numerical gpa range to description of required grade in letter-grade form
        below <letter> (when max < 4.0) (should check min < 0.7)
        <letter> or better (when min is > 0.7) (should check max >= 4.0)
        TODO Report anything that doesn't fit one of those two models
        GPA Letter 3×GPA
        4.3 A+      12.9
        4.0 A       12.0
        3.7 A-      11.1
        3.3 B+       9.9
        3.0 B        9.0
        2.7 B-       8.1
        2.3 C+       6.9
        2.0 C        6.0
        1.7 C-       5.1
        1.3 D+       3.9
        1.0 D        3.0
        0.7 D-       2.1
  """
  if max_gpa >= 4.0:
    if min_gpa > 1.0:
      letter = letters[int(round(min_gpa * 3))]
      return letter + ' or above in'
    else:
      return 'Pass'
  letter = letters[int(round(max_gpa * 3))]
  return 'below ' + letter + ' in'


# format_rules()
# -------------------------------------------------------------------------------------------------
def format_rules(rules):
  """ Generate HTML table with information about each transfer rule.
  """
  table = """
    <table id="rules-table">
      <thead>
        <tr>
          <th>Sending</th>
          <th>Courses</th>
          <th></th>
          <th>Receiving</th>
          <th>Courses</th><th>Review Status</th>
        </tr>
      </thead>
      <tbody>
      """
  for rule in rules:
    # The id attribute for each table row is the rule_key plus lists of course_ids:
    #   Source Institution        |
    #   hyphen                    |
    #   Destination Institution   | R K
    #   hyphen                    | U E
    #   Subject Area              | L Y
    #   hyphen                    | E
    #   Group Number              |
    #   hyphen
    #   Colon-separated list of source course_ids
    #   hyphen
    #   Colon-separated list of destination courses_ids
    row, description = format_rule(rule)
    table += row
  table += '</tbody></table>'
  return table


# format_rule_by_key()
# -------------------------------------------------------------------------------------------------
def format_rule_by_key(rule_key):
  """ Generate a rule tuple given the key.
  """
  rule_id = rule_ids[rule_key]
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  cursor.execute("""select t.*, s.source_course_ids, d.destination_course_ids
                      from transfer_rules t, view_source_courses s, view_destination_courses d
                     where t.id = %s
                       and t.id = s.rule_id
                       and t.id = d.rule_id
                     order by t. source_institution, t.destination_institution, t.subject_area
                 """, (rule_id, ))
  return format_rule(cursor.fetchone(), rule_key)


# format_rule()
# -------------------------------------------------------------------------------------------------
def format_rule(rule, rule_key=None):
  """ Return two strings, one that represents the rule as a table row and one that is a descriptive
      paragraph.
  """
  if rule_key is None:
    rule_key = '{}-{}-{}-{}'.format(rule.source_institution,
                                    rule.destination_institution,
                                    rule.subject_area,
                                    rule.group_number)

  # In case there are cross-listed courses to look up
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

  # Extract disciplines and courses from the rule
  source_disciplines = rule.source_disciplines.strip(':').split(':')
  source_courses = rule.source_courses
  destination_courses = rule.destination_courses

  # Check validity of Source and Destination course_ids
  source_course_ids = [course.course_id for course in rule.source_courses]
  # There should be no duplicates in source_course_ids for the rule
  assert len(set(source_course_ids)) == len(source_course_ids), \
      f'Duplcated source course id(s) for rule {rule_key}'
  source_course_id_str = ', '.join([f'{id}' for id in source_course_ids])

  destination_course_ids = [course.course_id for course in rule.destination_courses]
  # There should be no duplicates in destination_course_ids for the rule
  assert len(set(destination_course_ids)) == len(destination_course_ids), \
      f'Duplcated destination course id(s) for rule {rule_key}'

  # Figure out what discipline to list first in the case of multiple disciplines or cross-listings
  primary_discipline = source_courses[0].discipline   # default
  if rule.subject_area in source_disciplines:
    primary_discipline = rule.subject_area
  else:
    # Take the most frequently occurring discipline if there is a choice
    if len(source_disciplines) > 1:
      num_courses = dict([(d, 0) for d in source_disciplines])
      for source_course in source_courses:
        num_courses[source_course.discipline] += 1
      primary_discipline = sorted(num_courses.items(), key=lambda kv: kv[1])[0][0]

  #  Check for cross-listed source courses. Look up their disciplines and catalog_numbers.
  cross_listed_with = dict()
  for course in source_courses:
    if course.offer_count > 1:
      cursor.execute('select discipline, catalog_number from courses where course-id = $s',
                     (course.course_id,))
      assert cursor.rowcount == course.offer_count, \
          f'cross-listed source course counts do not match'
      cross_listed_with[course.course_id] = cursor.fetchall()
      print('*** source cross-listing:\n', course, cross_listed_with[course.course_id])

  # Now to figure out what to do with this nice list of source course cross-listings ... which also
  # are still in source_courses. The one with the primary_discipline stays in source_courses and
  # gets removed from cross_listed_with. The ones in cross_listed_with get removed from
  # source_courses. If the same discipline is repeated in the cross-listing, retain the one with the
  # lowest catalog number in source_courses.
  for course_id in cross_listed_with.keys():
    primary_course = None
    # Find first course with primary_discipline (there has to be one)
    for course in cross_listed_with[course_id]:
      if course.discipline == primary_discipline:
        primary_course = course
        break
    assert primary_course is not None, \
        f'Failed to find primary course in {cross_listed_with[course_id]}'
    # Find the primary course with the lowest catalog_number
    for course in cross_listed_with[course_id]:
      if course.discipline == primary_discipline and course.cat_num < primary_course.cat_num:
        primary_course = course
    # Remove primary_course from cross_listed_with and remove remaining cross_listed_with courses
    # from source_courses
    cross_listed_with[course_id].remove(primary_course)
    for course in cross_listed_with[course_id]:
      source_courses.remove(course)

  source_class = ''  # for the HTML credit-mismatch indicator

  # The course ids parts of the table row id
  row_id = '{}-{}-{}'.format(rule_key, source_course_ids, destination_course_ids)
  min_source_credits = 0.0
  max_source_credits = 0.0
  source_course_list = ''

  # All source courses do not necessarily have the same discipline.
  # Grade requirement can chage as the list of courses is traversed.
  # If course has cross-listings, list cross-listed course(s) in parens following the
  # catalog number. AND-list within a list of courses having the same grade requirement. OR-list
  # for cross-listed courses.
  # Examples:
  #   Passing grades in LCD 101 (=ANTH 101 or CMLIT 207) and LCD 102.
  #   Passing grades in LCD 101 (=ANTH 101) and LCD 102. C- or better in LCD 103.

  # First group courses by grade requirement. Not sure there will ever be a mix for one rule, if it
  # ever happens, we’ll be ready.
  courses_by_grade = dict()
  for course in source_courses:
    # Accumulate min/max credits for checking against destination credits
    min_source_credits += float(course.min_credits)
    max_source_credits += float(course.max_credits)
    if (course.min_gpa, course.max_gpa) not in courses_by_grade.keys():
      courses_by_grade[(course.min_gpa, course.max_gpa)] = []
    courses_by_grade[(course.min_gpa, course.max_gpa)].append(course)
  # For each grade requirement, sort by cat_num, and generate array of strings to AND-list together
  by_grade_keys = [key for key in courses_by_grade.keys()]
  by_grade_keys.sort()

  for key in by_grade_keys:
    grade_str = _grade(key[0], key[1])
    courses = courses_by_grade[key]
    courses.sort(key=lambda c: c.cat_num)
    course_list = []
    for course in courses:
      course_str = f'{course.discipline} {course.catalog_number}'
      if course.course_id in cross_listed_with.keys():
        xlist_courses = []
        for xlist_course in cross_listed_with[course.course_id]:
          xlist_courses.append(f'{xlist_course.discipline} {xlist_course.catalog_number}')
        course_str += '(=' + andor_list(xlist_courses, "or") + ')'
      course_list.append(f'<span title="course_id={course.course_id}">{course_str}</span>')
    source_course_list += f'{grade_str} {andor_list(course_list, "and")}'

  # If it’s a variable-credit course, what to do?
  # =======================================================================
  # How often does it happen? 1,859 times.
  # So just check if the transfer credits is in the range of min to max.

  # Build the destination part of the rule group
  destination_credits = 0.0
  discipline = ''
  destination_course_list = ''
  for course in destination_courses:
    course_catalog_number = course.catalog_number
    if discipline != course.discipline:
      if discipline != '':
        destination_course_list = destination_course_list.strip('/') + '; '
      discipline = course.discipline
      discipline_str = '<span title="{}">{}</span>'.format(course.discipline_name,
                                                           course.discipline)
      destination_course_list = destination_course_list.strip('/ ') + discipline_str + '-'

    if abs(float(course.min_credits) - course.transfer_credits) > 0.09:
      course_catalog_number += ' ({} cr.)'.format(course.transfer_credits)
    destination_course_list += \
        '<span title="course id: {}">{}</span>/'.format(course.course_id, course_catalog_number)

    destination_credits += float(course.transfer_credits)

  destination_course_list = destination_course_list.strip('/')

  row_class = 'clickable rule'
  if destination_credits < min_source_credits or destination_credits > max_source_credits:
    row_class = 'rule credit-mismatch'

  if min_source_credits != max_source_credits:
    source_credits_str = f'{min_source_credits}-{max_source_credits}'
  else:
    source_credits_str = f'{min_source_credits}'

  # If the rule has been evaluated, the last column is a link to the review history. But if it
  # hasn't been evaluated yet, the last column is just the text that says so.
  status_cell = status_string(rule.review_status)
  if rule.review_status != 0:
    status_cell = '<a href="/history/{}" target="_blank">{}</a>'.format(rule_key,
                                                                        status_cell)
  status_cell = '<span title="{}">{}</span>'.format(rule_key, status_cell)
  row = """<tr id="{}" class="{}">
              <td title="{}">{}</td>
              <td>{}</td>
              <td title="{}">=></td>
              <td title="{}">{}</td>
              <td>{}</td>
              <td>{}</td>
            </tr>""".format(row_id, row_class,
                            institution_names[rule.source_institution],
                            rule.source_institution.rstrip('0123456789'),
                            source_course_list,
                            '{} cr. :: {} cr.'
                            .format(source_credits_str, destination_credits),
                            institution_names[rule.destination_institution],
                            rule.destination_institution.rstrip('0123456789'),
                            destination_course_list,
                            status_cell)
  description = """
        <div class="{}">
          {} at {}, {} credits, transfers to {} as {}, {} credits.
        </div>""".format(row_class,
                         source_course_list,
                         institution_names[rule.source_institution],
                         source_credits_str,
                         institution_names[rule.destination_institution],
                         destination_course_list,
                         destination_credits)
  description = description.replace('Pass', 'Passing grade in')
  return row, description


if __name__ == "__main__":
  parser = argparse.ArgumentParser('Testing transfer rule groups')
  parser.add_argument('--debug', '-d', action='store_true', default=False)
  args = parser.parse_args()

  if args.debug:
    DEBUG = true

  print('Unit test not implemented')
