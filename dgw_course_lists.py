#! /usr/local/bin/python3

import sys

def requirements_to_html(row):
  """ Given a result row from the query in requirements(), generate html for the scribe block and
      the lists of head and body objects
  """
  if row.requirement_html == 'Not Available':
    return '<h1>This scribe block is not available.</h1><p><em>Should not occur.</em></p>'
  if len(row.head_objects) == 0 and len(row.body_objects) == 0:
    return row.requirement_html + '<p>This block has not been analyzed yet.</p>'
  head_course_lists = """
<section>
  <h1 class="closer">Head Objects</h1>
  <div>
    <hr>
    <section>
"""
  for course_list in row.head_objects:
    table_lists = course_list_to_tables(course_list)
    head_course_lists += f'<pre><h3>{course_list["object_type"].replace("_", " ").title()}</h3>'
    head_course_lists += f'               Context: {course_list["context_path"]}\n'

    head_course_lists += f'   Num Scribed Courses: {len(course_list["scribed_courses"]):>4}\n'
    scribed_courses = f' {course_list["list_type"]} '.join([format_course(course)
                                                           for course in
                                                           course_list["scribed_courses"]])

    head_course_lists += (f'   Scribed Course List: {scribed_courses}\n')
    if len(course_list["including_courses"]) > 0:
      include_list = ' AND '.join([f'{course[0]} {course[1]}'
                                  for course in course_list["including_courses"]])
      head_course_lists += f'          Must Include: {include_list}\n'
    if len(course_list["except_courses"]) > 0:
      except_list = ' OR '.join([f'{course[0]} {course[1]}' for course in
                                course_list["except_courses"]])
      head_course_lists += f'      Must Not Include: {except_list}\n'

    head_course_lists += f'    Num Active Courses: {len(course_list["active_courses"]):>4}\n'
    active_courses = f' {course_list["list_type"]} '.join([format_course(course, active=True)
                                                           for course in
                                                           course_list["active_courses"]])
    head_course_lists += (f'    Active Course List: {active_courses}\n')

    if len(course_list["list_qualifiers"]) > 0:
      head_course_lists += f'       List Qualifiers: {", ".join(course_list["list_qualifiers"])}\n'
    head_course_lists += f'                 Label: {course_list["label"]}\n'
    if len(course_list["attributes"]) > 0:
      head_course_lists += f'  Attributes in Common: {", ".join(course_list["attributes"])}\n'
  head_course_lists += '</pre></section></div></section>'

  body_course_lists = """
<section>
  <h1 class="closer">Body Objects</h1>
  <div>
    <hr>
    <section>
"""
  for course_list in row.body_objects:
    table_lists = course_list_to_tables(course_list)
    body_course_lists += f'<pre><h3>{course_list["object_type"].replace("_", " ").title()}</h3>'
    body_course_lists += f'               Context: {course_list["context_path"]}\n'
    body_course_lists += f'   Num Scribed Courses: {len(course_list["scribed_courses"]):>4}\n'
    scribed_courses = f' {course_list["list_type"]} '.join([format_course(course)
                                                           for course in
                                                           course_list["scribed_courses"]])
    body_course_lists += (f'   Scribed Course List: {scribed_courses}\n')
    if len(course_list["including_courses"]) > 0:
      include_list = ' AND '.join([f'{course[0]} {course[1]}'
                                  for course in course_list["including_courses"]])
      body_course_lists += f'          Must Include: {include_list}\n'
    if len(course_list["except_courses"]) > 0:
      except_list = ', '.join([f'{course[0]} {course[1]}' for course in
                               course_list["except_courses"]])
      body_course_lists += f'      Must Not Include: {except_list}\n'

    body_course_lists += f'    Num Active Courses: {len(course_list["active_courses"]):>4}\n'
    active_courses = f' {course_list["list_type"]} '.join([format_course(course, active=True)
                                                           for course in
                                                           course_list["active_courses"]])
    body_course_lists += (f'    Active Course List: {active_courses}\n')

    if len(course_list["list_qualifiers"]) > 0:
      body_course_lists += f'       List Qualifiers: {", ".join(course_list["list_qualifiers"])}\n'
    body_course_lists += f'                 Label: {course_list["label"]}\n'
    if len(course_list["attributes"]) > 0:
      body_course_lists += f'  Attributes in Common: {", ".join(course_list["attributes"])}\n'
  body_course_lists += '</pre></section></div></section>'

  return row.requirement_html + head_course_lists + body_course_lists


def format_course(course_tuple, active=False):
  """
  """
  if not active:
    course = f'{course_tuple[0]} {course_tuple[1]}'
    if course_tuple[2] is not None:
      course += f' with({course_tuple[2]})'
  else:
    course = f'{course_tuple[2]} {course_tuple[3]}'
    if course_tuple[5] is not None:
      course += f' with({course_tuple[5]})'

  return course


def course_list_to_tables(course_list):
  """ A course list, generated by dgw_utils.build_course_list() is an object with the following
      structure:
        {'object_type': 'course_list',
         'scribed_courses': [],
         'list_type': AND | OR,
         'list_qualifiers': [],
         'label': None | str,
         'active_courses': [],
         'attributes': [],
         'context_path': str }
      This function generates an HTML table for displaying the scribed and active_courses for a
      course_list object.
  """
  if len(course_list['scribed_courses']) > 0:
    scribed_table = """
<table class="course-list-table"><tr><th>Course</th><th>With Clause</th></tr>
"""
    for scribed_course in course_list['scribed_courses']:
      scribed_table += """
  <tr>
    <td>{} {}</td>
    <td>{}</td>
  </tr>
""".format(scribed_course[0],
           scribed_course[1],
           scribed_course[2])
    scribed_table += '</table>'
  else:
    scribed_table = '<p class="error">Error: There are no scribed courses.</p>'

  if len(course_list['active_courses']) > 0:
    active_table = """
<table class="course-list-table"><tr><th>Course</th><th>With Clause</th></tr>
"""
    for active_course in course_list['active_courses']:
      active_table += """
  <tr>
    <td>{} {}</td>
    <td>{}</td>
  </tr>
""".format(active_course[0],
           active_course[1],
           active_course[2])
    active_table += '</table>'
  else:
    active_table = '<p>There are no active courses for this list.</p>'

  return {'scribed_courses': scribed_table,
          'active_courses': active_table}
