#! /usr/bin/env python3
""" Complete info about a course
"""
import psycopg
import sys
from psycopg.rows import namedtuple_row

with psycopg.connect('dbname=cuny_curriculum') as conn:
  with conn.cursor(row_factory=namedtuple_row) as cursor:

    cursor.execute('select * from designations')
    designations = {row.designation: row.description for row in cursor}

    cursor.execute('select * from cuny_institutions')
    colleges = {row.code: row.name for row in cursor}

    cursor.execute('select * from cuny_courses')
    # dict: key is course_id; each value is a list with rows for different course_ids
    cuny_courses = {}
    for row in cursor:
      cuny_courses.setdefault(row.course_id, []).append(row)


def expand_rd(rd):
  if rd == 'RLA':
    return 'This is a Liberal Arts course that does not satisfy a Pathways requirement.'
  if rd == 'RNL':
    return 'This is not a Liberal Arts course.'
  try:
    return f'{designations[rd]}'
  except KeyError:
    return 'Unknown Designation!'


def _course_info(course_id_str: str):
  """ Return a table telling all about a course.
  """
  parts = course_id_str.split(':')
  course_id = int(parts[0])
  offer_nbr = int(parts[1]) if len(parts) == 2 else 1
  try:
    courses = cuny_courses[course_id]
    # All offer_nbrs
    offer_nbrs = [course.offer_nbr for course in courses]
    # Put requested offer_nbr first
    offer_nbrs = [offer_nbr] + [n for n in offer_nbrs if n != offer_nbr]
    assert offer_nbrs[0] == offer_nbr, 'Logic error'
    courses.sort(key=lambda c: offer_nbrs.index(c.offer_nbr))

    # Assemble course info, starting with requested offer_nbr
    for course in courses:
      college = colleges[course.institution]
      title = (f'<h1>{college} {course.discipline} {course.catalog_number}: '
               f'<em>{course.title}</em></h1>\n')
      result = '<table><tr><th>Property</th><th>Value</th></tr>\n'
      if course.offer_nbr != offer_nbr:
        result += ('<tr><th>Cross-listed with</th><td>' + '<br>'.join([f'{course.discipline} ',
                                                                       f'{course.catalog_number}'])
                   + '</td></tr>\n')
      result += f'<tr><th>Description</th><td> {course.description} </td></tr>\n'
      gened_text = expand_rd(course.designation)
      result += f'<tr><th>General Education</th><td> {gened_text} </td></tr>\n'
      result += '<tr><th>Transfers To</th><td> ... </td></tr>\n'
      result += '<tr><th>Transfers From</th><td> ... </td></tr>\n'
      wric = 'Yes' if 'WRIC' in course.attributes else 'No'
      result += f'<tr><th>Writing Intensive</th><td>{wric}</td></tr>\n'
      result += '</table>'

  except KeyError:
    title = '<h1 class="error">Course not found</h1>'
    result = '<p>The course you requested does not appear to match any course in CUNYfirst.</p>'
    result += f'<p>{course_id}:{offer_nbr}'

  return title, result


if __name__ == '__main__':
  # Get course_id and, optionally, offer_nbr from command args or user.
  if len(sys.argv) > 1:
    course_id = ':'.join(sys.argv[1:])
  else:
    course_id = input('course_id: ')
  if ':' not in course_id:
    course_id += ':1'
  parts = _course_info(course_id)
  html = f"""
  <!doctype html>
  <html lang="en">
    <head>
      <title>testing</title>
      <meta charset="utf-8" />
    </head>
    <body>
      {parts[0]}
      {parts[1]}
    </body>
  </html>
  """
  print(html, file=sys.stderr)
