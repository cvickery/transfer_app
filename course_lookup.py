from pgconnection import pgconnection
from psycopg2.extras import NamedTupleCursor

from collections import namedtuple

import math
import re
from time import time

""" Globals
    ----------------------------------------------------------------
"""
conn = pgconnection('dbname=cuny_courses')
cursor = conn.cursor(cursor_factory=NamedTupleCursor)

# Create list of all cross-listed courses’s course_ids
query = """
  select course_id from courses
  where offer_nbr > 1 and offer_nbr < 5
  group by course_id
  order by course_id
        """
cursor.execute(query)
cross_listed = [id.course_id for id in cursor.fetchall()]
cursor.close()
conn.close()

Course_Info = namedtuple('Course_Info',
                         """
                            course_id
                            exists
                            is_active
                            career
                            institution_prompt
                            institution
                            cuny_subject
                            department
                            discipline
                            catalog_number
                            title
                            contact_hours
                            min_credits
                            max_credits
                            requisites
                            description
                            rd
                            designation
                            attributes
                            attribute_descriptions
                            title_str
                            html
                         """)
# default values, except for course_id, which is required
Course_Info.__new__.__defaults__ = (False,                  # exists
                                    False,                  # is_active
                                    '',                     # career
                                    'None',                 # institution_prompt
                                    'No Institution',       # institution
                                    'No Subject',           # cuny_subject
                                    'No Department',        # department
                                    'No Discipline',        # discipline
                                    'No Number',            # catalog_number
                                    'No Title',             # title
                                    'Not in CUNY Catalog',  # title_str
                                    '',                     # hours_credits_str
                                    '',                     # credit_details
                                    '',                     # description
                                    '',                     # attributes
                                    '<p class="catalog-entry"> Not in CUNY Catalog</p>'  # html
                                    )


def lookup_courses(institution):
  """ Lookup all the active courses for an institution. Return giant html string.
  """
  start = time()
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  course_cursor = conn.cursor(cursor_factory=NamedTupleCursor)   # for attribute queries

  html = ''

  # print(f'cross-listed courses at {institution}: {cross_listed}')

  institution_query = """
  select  c.course_id                       as course_id,
          c.offer_nbr                       as offer_nbr,
          i.name                            as institution,
          s.description                     as cuny_subject,
          d.description                     as department,
          c.discipline                      as discipline,
          trim(both from c.catalog_number)  as catalog_number,
          c.title                           as title,
          c.primary_component               as primary_component,
          c.components                      as components,
          c.min_credits                     as min_credits,
          c.max_credits                     as max_credits,
          c.requisites                      as requisites,
          c.description                     as description,
         cc.description                     as career,
          c.designation                     as rd,
         rd.description                     as designation,
          c.course_status                   as course_status,
          c.attributes                      as attributes,
          c.attribute_descriptions          as attribute_descriptions

    from  courses           c,
          institutions      i,
          cuny_departments  d,
          cuny_subjects     s,
          cuny_careers      cc,
          designations      rd
   where  c.institution = %s
     and  c.course_status = 'A'
     and  c.can_schedule = 'Y'
     and  c.discipline_status = 'A'
     and  i.code = c.institution
     and  d.institution = c.institution
     and  d.department = c.department
     and  s.subject = c.cuny_subject
     and  cc.institution = c.institution
     and  cc.career = c.career
     and  rd.designation = c.designation
   order by discipline, catalog_number
  """

  cursor.execute(institution_query, (institution,))
  Row = namedtuple('Row', [c.name for c in cursor.description])

  first_query = time()
  for row in cursor.fetchall():
    course = Row._make(row)

    # if one of the components is the primary component (it should be), make it the first one.
    components = course.components
    if len(course.components) > 1:
      components = dict(course.components)
      primary_component = [course.primary_component,
                           components.pop(course.primary_component, None)]
      components = [[component, components[component]] for component in components.keys()]
      components.insert(0, primary_component)
    component_str = ', '.join([f'{component[1]} hr {component[0].lower()}' for component in components])
    if math.isclose(course.min_credits, course.max_credits):
      credits_str = f'{component_str}; {course.min_credits:0.1f} cr.'
    else:
      credits_str = f'{component_str}; {course.min_credits:0.1f}–{course.max_credits:0.1f} cr'

    title_str = f"""
                  <strong>{course.discipline} {course.catalog_number}: {course.title}</strong>
                  (<em>{course.career}, {course.cuny_subject}, {course.attributes}</em>)
                  <br/>Requisites: {course.requisites}"""
    if course.course_id in cross_listed:
      # For cross-listed courses, it’s normal for the cuny_subject and requisites to change across
      # members of the group.
      # But it would be an error for career, requisites, description, designation, etc. to vary, so
      # we assume they don’t. (There are two known cases of career errors, which OUR is correctins
      # as we speak. There are no observed  errors of the other types.)
      # There is no way to get a different attributes list, because those depend only on course_id.
      title_str += '<br/>Cross-listed with:'
      course_cursor.execute("""
                            select c.discipline, c.catalog_number, c.title,
                              cc. description as career, s.description as cuny_subject,
                              c.designation, c.requisites, c.attributes
                            from courses c, cuny_subjects s, cuny_careers cc
                            where course_id = %s
                            and offer_nbr != %s
                            and cc.career = c.career
                            and  cc.institution = c.institution
                            and s.subject = c.cuny_subject
                            order by discipline, catalog_number""",
                            (course.course_id, course.offer_nbr))
      for cross_list in course_cursor.fetchall():
        title_str += f"""<br/>
        <strong>{cross_list.discipline} {cross_list.catalog_number}: {cross_list.title}</strong>
        (<em>{cross_list.career}, {cross_list.cuny_subject}, {cross_list.attributes}</em>)
        <br/>Requisites: {cross_list.requisites}
        """

    html = html + """
    <p class="catalog-entry" title="course id: {}">{}
      <br/>{}
      <br/>{}
    </p>
    """.format(course.course_id,
               title_str,
               credits_str,
               course.description)
  cursor.close()
  conn.close()
  end = time()

  return html


def lookup_course(course_id):
  """ Lookup a course and returned a named tuple with lotso info about it.
  """
  query = """
    select  i.prompt                          as institution_prompt,
            i.name                            as institution,
            s.description                     as cuny_subject,
            d.description                     as department,
            c.discipline                      as discipline,
            trim(both from c.catalog_number)  as catalog_number,
            c.title                           as title,
            c.hours                           as hours,
            c.min_credits                     as min_credits,
            c.max_credits                     as max_credits,
            c.credits                         as progress_units,
            c.fa_credits                      as fin_aid_units,
            c.requisites                      as requisites,
            c.description                     as description,
           cc.description                     as career,
            c.designation                     as rd,
           rd.description                     as designation,
            c.course_status                   as course_status

      from  courses           c,
            institutions      i,
            cuny_departments  d,
            cuny_subjects     s,
            cuny_careers      cc,
            designations      rd
     where  c.course_id = %s
       and  i.code = c.institution
       and  d.institution = c.institution
       and  d.department = c.department
       and  s.subject = c.cuny_subject
       and  cc.institution = c.institution
       and  cc.career = c.career
       and  rd.designation = c.designation
  """
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  try:
    course_id = int(course_id)
  except ValueError:
    return (Course_Info(course_id, False))  # invalid course_id
  cursor.execute(query, (course_id,))
  Row = namedtuple('Row', [c.name for c in cursor.description])
  if cursor.rowcount == 1:
    row = Row._make(cursor.fetchone())

    # Have to collect attribute(s) separately 'cause there might be multiple rows
    cursor.execute("""
              select a.attribute_name, a.attribute_value, a.description
              from attributes a, course_attributes c
              where c.course_id = %s
                and c.name = a.attribute_name
                and c.value = a.attribute_value
              """, (course_id, ))
    the_attributes = [row[2] for row in cursor.fetchall()]
    attributes = ''
    if the_attributes is None or len(the_attributes) == 0:
      pass
    else:
      for attribute in the_attributes:
        attributes += """
          <div class="catalog-entry"><strong>Attribute:</strong> {}</div>\n""".format(attribute)

    cursor.close()
    conn.close()

    if isclose(row.min_credits, row.max_credits):
      credits_str = f'{row.min_credits:0.1f}'
      hours_credits_str = f'{row.hours:0.1f}hr; {row.min_credits:0.1f}cr;'
    else:
      credits_str = f'{row.min_credits:0.1f}–{row.max_credits:0.1f}'
      hours_credits_str = f'{row.hours:0.1f}hr; {row.min_credits:0.1f}–{row.max_credits:0.1f}cr;'

    html = """
    <p class="catalog-entry" title="course id: {}"><strong>{} {}: {}</strong> (<em>{}; {}</em>)
    <br/>
    {} Requisites: <em>{}</em><br/>{} (<em>{}</em>)<br/>Attributes: {}</p>
    """.format(course_id,
               row.discipline,
               catalog_number,
               row.title,
               row.career,
               row.cuny_subject,
               hours_credits_str,
               row.requisites,
               row.description,
               row.designation,
               attributes)

    title_str = """course_id {}: {} {} {} {:0.1f}hr;{}cr""".format(course_id,
                                                                   row.discipline,
                                                                   row.catalog_number,
                                                                   row.title,
                                                                   row.hours,
                                                                   credits_str)

    return Course_Info(course_id,                 # course_id
                       True,                      # exists
                       row.course_status == 'A',  # is_active
                       row.career,                # career
                       row.institution_prompt,    # institution_prompt
                       row.institution,           # institution
                       row.cuny_subject,          # cuny_subject
                       row.department,            # department
                       row.discipline,            # discipline
                       row.catalog_number,        # catalog_number
                       row.title,                 # title
                       row.hours,                 # hours
                       row.min_credits,           # min_credits
                       row.max_credits,           # max_credits
                       row.progress_units,        # progress_units
                       row.fin_aid_units,         # fin_aid_units
                       row.requisites,            # requisites
                       row.description,           # description
                       row.rd,                    # rd
                       row.designation,           # designation
                       attributes,                # attributes
                       title_str,                 # title_str
                       html                       # html
                       )
  else:
    return Course_Info(course_id, False)

# CUNYCourse
# -------------------------------------------------------------------------------------------------
# class CUNYCourse:
#   """ Catalog and related info for a CUNYfirst course.
#       NOTE: with the introduction of lookup_course, the need for this wrapper class is low to nil.

#       Exposed fields and methods:
#         course_id           int
#         exists              bool
#         is_active           bool
#         institution_prompt
#         institution
#         cuny_subject
#         department
#         discipline
#         catalog_number
#         title
#         hours               float
#         min_credits         float
#         max_credits         float
#         progress_units      float
#         fa_units            float
#         requisites
#         description
#         rd
#         designation
#         attributes
#         title_str           html title attribute
#         html                terse catalog description
#   """
#   def __init__(self, course_id):
#     """ Get complete information for a course from cuny_courses db.
#     """
#     info = lookup_course(course_id)
#     self.course_id = info.course_id
#     self.exists = info.exists
#     self.is_active = info.is_active
#     self.career = info.career
#     self.institution_prompt = info.institution_prompt
#     self.institution = info.institution
#     self.cuny_subject = info.cuny_subject
#     self.department = info.department
#     self.discipline = info.discipline
#     self.catalog_number = info.catalog_number
#     self.title = info.title
#     self.hours = info.hours
#     self.min_credits = info.min_credits
#     self.max_credits = info.max_credits
#     self.progress_units = info.progress_units
#     self.fin_aid_units = info.fin_aid_units
#     self.requisites = info.requisites
#     self.description = info.description
#     self.rd = info.rd
#     self.designation = info.designation
#     self.attributes = info.attributes
#     self.title_str = info.title_str
#     self.html = info.html

#   def __str__(self):
#     return self.html

#   def course_id(self):
#     return self.course_id
#   def is_active(self):
#     return self.is_active
#   def institution(self):
#     return self.institution
#   def department(self):
#     return self.department


if __name__ == '__main__':
  import sys
  try:
    courses = lookup_courses(sys.argv[1])
    print(courses)
  except Exception as e:
    print(e)
    print('Usage: python cuny_course.py institution')
