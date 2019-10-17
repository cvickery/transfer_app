#! /usr/local/bin/python3
from collections import namedtuple
import json
import re
import argparse

from flask import session
from pgconnection import pgconnection
from reviews_status_utils import status_string
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
                           discipline_name
                           """)

Destination_Course = namedtuple('Destination_Course', """
                                course_id
                                offer_count
                                discipline
                                catalog_number
                                cat_num
                                cuny_subject
                                transfer_credits
                                discipline_name
                                """)

conn = pgconnection('dbname=cuny_courses')
cursor = conn.cursor()
cursor.execute("select code, prompt from institutions order by lower(name)")
institution_names = {row.code: row.prompt for row in cursor}
# cursor.execute('select * from transfer_rules')
# rule_ids = dict()
# for rule in cursor.fetchall():
#   rule_ids['{}-{}-{}-{}'.format(rule.source_institution,
#                                 rule.destination_institution,
#                                 rule.subject_area,
#                                 rule.group_number)] = rule.id
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
  return_str = ', '.join(items)
  k = return_str.rfind(',')
  if k > 0:
    k += 1
    return_str = return_str[:k] + f' {andor}' + return_str[k:]
  if return_str.count(',') == 1:
    return_str = return_str.replace(',', '')
  return return_str


# _grade()
# -------------------------------------------------------------------------------------------------
def _grade(min_gpa, max_gpa):
  """ Convert numerical gpa range to description of required grade in letter-grade form.
      The issue is that gpa values are not represented uniformly across campuses, and the strings
      used have to be floating point values, which lead to imprecise boundaries between letter
      names.
        “<letter> or above” when min is > 0.7 and max is 4.0+
        “below <letter>” when min is 0.7 and max is < 4.0
        “between <letter> and <letter>” when min is > 0.7 and max is < 4.0
        “Pass” when none of the above

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
  # Put gpa values into “canonical form”
  assert min_gpa <= max_gpa, f'min_gpa {min_gpa} greater than {max_gpa}'
  # Courses transfer only if the student passed the course, so force the min acceptable grade
  # to be a passing (D-) grade.
  if min_gpa < 1.0:
    min_gpa = 0.7
  if max_gpa > 4.0:
    max_gpa = 4.0

  # Generate the letter grade requirement string
  if min_gpa > 0.7 and max_gpa > 3.9:
    letter = letters[int(round(min_gpa * 3))]
    return f'{letter} or above in'
  if min_gpa < 0.8 and max_gpa < 3.9:
    letter = letters[int(round(max_gpa * 3))]
    return 'below ' + letter + ' in'
  if min_gpa > 0.8 and max_gpa < 3.9:
    return f'between {letters[int(round(min_gpa * 3))]} and {letters[int(round(max_gpa * 3))]} in'
  return 'Pass'


# format_rules()
# -------------------------------------------------------------------------------------------------
def format_rules(rules, scrollable=False):
  """ Generate HTML table with information about each transfer rule.
  """

  # Sort the rules by discipline-cat-num of first source_course
  #   First, order by decreasing stringency of GPA requiements
  rules.sort(key=lambda r: (r.source_courses[0].min_gpa, r.source_courses[0].max_gpa), reverse=True)
  #   Then, order by increasing discipline-cat_num
  rules.sort(key=lambda r: (r.source_courses[0].discipline, r.source_courses[0].cat_num))

  # Generate the table
  if scrollable:
    class_attribute = ' class="scrollable"'
  else:
    class_attribute = ''
  table = f"""
    <table id="rules-table"{class_attribute}>
      <thead>
        <tr>
          <th>Sending</th>
          <th>Courses</th>
          <th>Credits</th>
          <th>Receiving</th>
          <th>Courses</th><th>Review Status</th>
        </tr>
      </thead>
      <tbody>
      """
  for rule in rules:
    row, description = format_rule(rule)
    table += row
  table += '</tbody></table>'
  return table


# format_rule_by_key()
# -------------------------------------------------------------------------------------------------
def format_rule_by_key(rule_key):
  """ Generate a Transfer_Rule tuple given the key.
  """
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  cursor.execute("""
  select * from transfer_rules
   where source_institution = %s
     and destination_institution = %s
     and subject_area = %s
     and group_number = %s
  """, rule_key.split('-'))
  rule = cursor.fetchone()

  cursor.execute("""
    select  sc.course_id,
            sc.offer_count,
            sc.discipline,
            sc.catalog_number,
            sc.cat_num,
            sc.cuny_subject,
            sc.min_credits,
            sc.max_credits,
            sc.min_gpa,
            sc.max_gpa,
            dn.discipline_name
    from source_courses sc, cuny_disciplines dn
    where sc.rule_id = %s
      and dn.institution = %s
      and dn.discipline = sc.discipline
    order by discipline, cat_num
    """, (rule.id, rule.source_institution))
  source_courses = [Source_Course._make(c)for c in cursor.fetchall()]

  cursor.execute("""
    select  dc.course_id,
            dc.offer_count,
            dc.discipline,
            dc.catalog_number,
            dc.cat_num,
            dc.cuny_subject,
            dc.transfer_credits,
            dn.discipline_name
     from destination_courses dc, cuny_disciplines dn
    where dc.rule_id = %s
      and dn.institution = %s
      and dn.discipline = dc.discipline
    order by discipline, cat_num
    """, (rule.id, rule.destination_institution))
  destination_courses = [Destination_Course._make(c) for c in cursor.fetchall()]

  the_rule = Transfer_Rule._make(
      [rule.id,
       rule.source_institution,
       rule.destination_institution,
       rule.subject_area,
       rule.group_number,
       rule.source_disciplines,
       rule.source_subjects,
       rule.review_status,
       source_courses,
       destination_courses])
  cursor.close()
  conn.close()
  return format_rule(the_rule, rule_key)


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
  source_course_id_str = ':'.join([f'{id}' for id in source_course_ids])

  destination_course_ids = [course.course_id for course in rule.destination_courses]
  # There should be no duplicates in destination_course_ids for the rule
  assert len(set(destination_course_ids)) == len(destination_course_ids), \
      f'Duplcated destination course id(s) for rule {rule_key}'
  destination_course_id_str = ':'.join([f'{id}' for id in destination_course_ids])
  #  Check for any cross-listed source courses. Look up their disciplines and catalog_numbers.
  cross_listed_with = dict()
  for course in source_courses:
    if course.offer_count > 1:
      cursor.execute("""select discipline, catalog_number, cuny_subject
                          from courses
                         where course_id = %s""",
                     (course.course_id,))
      assert cursor.rowcount == course.offer_count, \
          f'cross-listed source course counts do not match'
      cross_listed_with[course.course_id] = cursor.fetchall()

  source_class = ''  # for the HTML credit-mismatch indicator

  # The course ids parts of the table row id
  row_id = '{}-{}-{}'.format(rule_key, source_course_id_str, destination_course_id_str)
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

  # First group courses by grade requirement. Not sure there will ever be a mix for one rule, but
  # if it ever happens, we’ll be ready.
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
          if xlist_course.discipline != course.discipline or \
             xlist_course.catalog_number != course.catalog_number:
            xlist_courses.append(f'{xlist_course.discipline} {xlist_course.catalog_number}')
        course_str += '(=' + andor_list(xlist_courses, "or") + ')'
      course_list.append(f'<span title="course_id={course.course_id}">{course_str}</span>')
    source_course_list += f'{grade_str} {andor_list(course_list, "and")}'

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

    # if abs(float(course.min_credits) - course.transfer_credits) > 0.09:
    #   course_catalog_number += ' ({} cr.)'.format(course.transfer_credits)
    destination_course_list += \
        '<span title="course id: {}">{}</span>/'.format(course.course_id, course_catalog_number)

    destination_credits += float(course.transfer_credits)

  destination_course_list = destination_course_list.strip('/')

  row_class = 'rule'
  if destination_credits < min_source_credits or destination_credits > max_source_credits:
    row_class += ' credit-mismatch'

  if min_source_credits != max_source_credits:
    source_credits_str = f'{min_source_credits}-{max_source_credits}'
  else:
    source_credits_str = f'{min_source_credits}'

  # If the rule has been evaluated, the last column is a link to the review history. But if it
  # hasn’t been evaluated yet, the last column is just the text that says so.
  status_cell = status_string(rule.review_status)
  if rule.review_status != 0:
    status_cell = f"""<a href="{session['base_url']}history/{rule_key}">{status_cell}</a>"""
  status_cell = '<span title="{}">{}</span>'.format(rule_key, status_cell)
  row = """<tr id="{}" class="{}">
              <td title="{}">{}</td>
              <td>{}</td>
              <td>{}</td>
              <td title="{}">{}</td>
              <td>{}</td>
              <td>{}</td>
            </tr>""".format(row_id, row_class,
                            institution_names[rule.source_institution],
                            rule.source_institution.rstrip('0123456789'),
                            source_course_list,
                            f'{source_credits_str} => {destination_credits}',
                            institution_names[rule.destination_institution],
                            rule.destination_institution.rstrip('0123456789'),
                            destination_course_list,
                            status_cell)
  description = f"""<span class="{row_class} description">{source_course_list}
        at {institution_names[rule.source_institution]},
        {source_credits_str} credits, transfers to
        {institution_names[rule.destination_institution]}
        as {destination_course_list}, {destination_credits} credits.</span>"""
  description = description.replace('Pass', 'Passing grade in')
  return row, description


if __name__ == '__main__':
  parser = argparse.ArgumentParser('Testing transfer rules')
  parser.add_argument('--debug', '-d', action='store_true', default=False)
  parser.add_argument('--grade', '-g', nargs=2)
  args = parser.parse_args()

  if args.debug:
    DEBUG = true
  if args.grade:
    min_gpa = float(args.grade[0])
    max_gpa = float(args.grade[1])
    print(f'"{_grade(min_gpa, max_gpa)}"')
