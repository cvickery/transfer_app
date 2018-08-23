
from collections import namedtuple
import json
import re
import argparse

from course_lookup import lookup_course
from pgconnection import pgconnection
from status_utils import status_string

DEBUG = False

Rule_Info = namedtuple('Rule_Info', """
                        source_institution
                        source_discipline
                        group_number
                        destination_institution
                        status""")

# Source_Course = namedtuple('Source_Course', """
#                            course_id
#                            discipline
#                            discipline_name
#                            catalog_number
#                            min_credits
#                            max_credits
#                            min_gpa
#                            max_gpa
#                            """)
# Destination_Course = namedtuple('Destination_Course', """
#                                 course_id
#                                 discipline
#                                 discipline_name
#                                 catalog_number
#                                 min_credits
#                                 max_credits
#                                 transfer_credits""")

letters = ['F', 'F', 'D-', 'D', 'D+', 'C-', 'C', 'C+', 'B-', 'B', 'B+', 'A-', 'A', 'A+']

conn = pgconnection('dbname=cuny_courses')
cursor = conn.cursor()
cursor.execute("select code, prompt from institutions order by lower(name)")
institution_names = {row.code: row.prompt for row in cursor}
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
def format_rules(rules, session):
  """ Generate HTML table with information about each rule group.
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
    # The id for the row will be the rule id plus lists of course_ids:
    #   Source institution
    #   hyphen
    #   Source Discipline
    #   hyphen
    #   Group number
    #   hyphen
    #   Destination institution
    #   hyphen
    #   Colon-separated list of source course_ids
    #   hyphen
    #   Colon-separated list of destination courses_ids
    print(rule)
    row, description = format_rule(rule)
    table += row
  table += '</tbody></table>'
  return table


# format_rule()
# -------------------------------------------------------------------------------------------------
def format_rule(rule):
  """ Return strings that represent the rule as a table row and as a descriptive paragraph.
  """
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

  # Get lists of source and destination courses for this rule group
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
       where  sc.rule_id = %s
         and  %s ~ c.course_id::text
         and  sc.course_id = c.course_id
       order by c.discipline,
                sc.max_gpa desc,
                substring(c.catalog_number from '\d+\.?\d*')::float
       """
  cursor.execute(q, (rule.rule_id, rule.source_course_ids))
  source_courses = cursor.fetchall()

  # groups.sort(key=lambda g: (g.source_institution,
  #                            g.source_discipline,
  #                            g.source_courses[0].catalog_number))

  q = """
      select  c.course_id,
              c.discipline,
              d.description as discipline_name,
              trim(c.catalog_number) as catalog_number,
              c.min_credits,
              c.max_credits,
              dc.transfer_credits
        from  courses c, disciplines d, destination_courses dc
       where  dc.rule_id = %s
         and  %s ~ c.course_id::text
         and  dc.course_id = c.course_id
       order by discipline, substring(c.catalog_number from '\d+\.?\d*')::float
       """
  cursor.execute(q, (rule.rule_id, rule.destination_course_ids))
  destination_courses = cursor.fetchall()

  # The course ids parts of the table row id
  row_id = '{}-{}-{}'.format(rule.rule_str, rule.source_course_ids, rule. destination_course_ids)
  print('format_rule: row_id is:', row_id)
  min_source_credits = 0.0
  max_source_credits = 0.0
  grade = ''
  discipline = ''
  catalog_number = ''
  source_course_list = ''

  # Source course strings: All the courses have the same discipline, so that gets listed once,
  # with catalog numbers separated by slashes.
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
    status_cell = '<a href="/history/{}" target="_blank">{}</a>'.format(rule.rule_str,
                                                                        status_cell)
  status_cell = '<span title="{}">{}</span>'.format(rule.rule_str, status_cell)
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
