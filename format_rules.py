
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
  """ Return two strings, one that represent the rule as a table row and one that is a descriptive
      paragraph.
  """
  if rule_key is None:
    rule_key = '{}-{}-{}-{}'.format(rule.source_institution,
                                    rule.destination_institution,
                                    rule.subject_area,
                                    rule.group_number)
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

  # Source Courses
  source_course_ids = [id for id in rule.source_course_ids.strip(':').split(':')]
  # There should be no duplicates in source_course_ids for the rule
  assert len(set(source_course_ids)) == len(source_course_ids), \
      f'Duplcated course id(s) for rule {rule_key}'

  # Get source disciplines covered by the rule
  source_disciplines = rule.source_disciplines.strip(':').split(':')

  q = """
      select  c.course_id,
              c.offer_nbr,
              c.discipline,
              d.description as discipline_name,
              trim(c.catalog_number) as catalog_number,
              c.min_credits,
              c.max_credits,
              sc.min_gpa,
              sc.max_gpa
       from   courses c, disciplines d, source_courses sc
       where  c.course_id in (%s)
         and  sc.rule_id = %s
         and  sc.course_id = c.course_id
         and  d.institution = c.institution
         and  d.discipline = c.discipline
       order by c.discipline,
                sc.max_gpa desc,
                substring(c.catalog_number from '\d+\.?\d*')::float
       """
  cursor.execute(q, (', '.join(source_course_ids), rule.id))
  source_courses = cursor.fetchall()

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
      print(f'*** {primary_discipline} ({num_courses[primary_discipline]}): {source_disciplines}')
  print(f'**** {primary_discipline}')
  #  Check for cross-listed courses (duplicated course_ids in query results)
  if len(source_courses) != len(source_course_ids):
    assert len(source_courses) > len(source_course_ids), \
        f'Not all courses found for rule {rule_key}'
    assert len(source_courses) > 0, \
        f'No courses found for rule {rule_key}'
    courses_by_id = copy(source_courses)
    courses_by_id.sort(key=lambda record: (record.course_id, record.offer_nbr))
    prev = -1
    cross_listed_with = dict()
    for course in courses_by_id:
      if course.course_id == prev:
        if prev not in cross_listed_with.keys():
          cross_listed_with[prev] = []
        cross_listed_with[prev].append(course)
      else:
        prev = course.course_id
  # Now to figure out what to do with this nice list of source course cross-listings ... which also
  # are still in source_courses.
  for course_id in cross_listed_with.keys():
    print(f'{course_id} is cross-listed with')
    for course in cross_listed_with[course_id]:
      print(f'  {course.offer_nbr}: {course.discipline} {course.catalog_number}')

  source_class = ''  # for the HTML credit-mismatch indicator

  # Destination Courses
  destination_course_ids = ', '.join(rule.destination_course_ids.strip(':').split(':'))
  q = """
      select  c.course_id,
              c.discipline,
              d.description as discipline_name,
              trim(c.catalog_number) as catalog_number,
              c.min_credits,
              c.max_credits,
              dc.transfer_credits
        from  courses c, disciplines d, destination_courses dc
       where  c.course_id in (%s)
         and  dc.course_id = c.course_id
         and  dc.rule_id = %s
         and  d.institution = c.institution
         and  d.discipline = c.discipline
       order by discipline, substring(c.catalog_number from '\d+\.?\d*')::float
       """
  cursor.execute(q, (destination_course_ids, rule.id))
  destination_courses = cursor.fetchall()

  # The course ids parts of the table row id
  row_id = '{}-{}-{}'.format(rule_key, rule.source_course_ids, rule.destination_course_ids)
  min_source_credits = 0.0
  max_source_credits = 0.0
  grade = ''
  discipline = ''
  catalog_number = ''
  source_course_list = ''

  # Source course strings: All the courses have the same discipline, so that gets listed once,
  # with catalog numbers separated by slashes.
  # TODO: fix for cross-listed courses. All courses do not necessarily have the same discipline.
  for course in source_courses:
    course_grade = _grade(course.min_gpa, course.max_gpa)
    if course_grade != grade:
      if grade != '':
        source_course_list = source_course_list.strip('/') + '; '
      grade = course_grade
      source_course_list = source_course_list.strip('/') + ' {} '.format(grade)

    if discipline != course.discipline:
      if discipline != '':
        source_course_list = source_course_list.strip('/') + '; '
      discipline = course.discipline
      discipline_str = '<span title="{}">{}</span>'.format(course.discipline_name,
                                                           course.discipline)
      source_course_list = source_course_list.strip('/') + discipline_str + '-'
    if catalog_number != course.catalog_number:
      catalog_number = course.catalog_number
      source_course_list += '<span title="course id: {}">{}</span>/'.format(course.course_id,
                                                                            course.catalog_number)

      # If it’s a variable-credit course, what to do?
      # =======================================================================
      # ?? how often does it happen? 1859 times.
      # So just check if the transfer credits is in the range of min to max.
      min_source_credits += float(course.min_credits)
      max_source_credits += float(course.max_credits)

  source_course_list = source_course_list.strip('/')

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

  row_class = 'rule'
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
