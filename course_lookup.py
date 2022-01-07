
import math
import re
import json
from time import time

from pgconnection import PgConnection

""" Globals
    ----------------------------------------------------------------
"""
conn = PgConnection()
cursor = conn.cursor()

# Public list of all cross-listed courses’s course_ids CUNY-wide
query = """
  select course_id from cuny_courses
  where offer_nbr > 1 and offer_nbr < 5
  group by course_id
  order by course_id
        """
cursor.execute(query)
cross_listed = [id.course_id for id in cursor.fetchall()]

# Public copy of the course_attributes table, formatted as table rows
cursor.execute('select * from course_attributes order by name, value')
course_attribute_rows = '\n    '.join([f"""
    <tr>
      <td>{r.name}</td><td>{r.value}</td><td>{r.description}</td>
    </tr>
    """ for r in cursor.fetchall()])
cursor.close()
conn.close()

# Course info for a single course_id
course_query = """
select  c.course_id                       as course_id,
        c.offer_nbr                       as offer_nbr,
        i.name                            as institution,
        s.subject_name                    as cuny_subject,
        d.department_name                 as department,
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
        c.attributes                      as attributes

  from  cuny_courses      c,
        cuny_institutions i,
        cuny_departments  d,
        cuny_subjects     s,
        cuny_careers      cc,
        designations      rd

 where  c.course_id = %s
   and  c.offer_nbr = %s
   {}
   and  i.code = c.institution
   and  d.institution = c.institution
   and  d.department = c.department
   and  s.subject = c.cuny_subject
   and  cc.institution = c.institution
   and  cc.career = c.career
   and  rd.designation = c.designation
 order by discipline, numeric_part(catalog_number)
"""


# lookup_course()
# --------------------------------------------------------------------------------------------------
def lookup_course(course_id, active_only=False, offer_nbr=1):
  """ Get HTML for one course_id. In the case of cross-listed courses, give the one with offer_nbr
      equal to 1 unless overridden.
  """
  conn = PgConnection()
  cursor = conn.cursor()

  # Active courses require both the course and the discipline to be active
  if active_only:
    which_courses = """
    and  c.course_status = 'A'
    and  c.discipline_status = 'A'
    """
  else:
    which_courses = ''

  cursor.execute(course_query.format(which_courses), (course_id, offer_nbr))
  if cursor.rowcount == 0:
    print('COURSE LOOKUP FAILED', cursor.query)
    return None

  if cursor.rowcount > 1:
    raise Exception(f'lookup_course() found {cursor.rowcount} courses for {course_id}:{offer_nbr}')

  course = cursor.fetchone()
  conn.close()

  html = format_course(course)
  return [course, html]


# lookup_courses()
# --------------------------------------------------------------------------------------------------
def lookup_courses(institution, active_only=True, department=None, discipline=None):
  """ Lookup all the active courses for an institution. Return giant html string.
      Can restrict to courses offered by a particular department and/or in a particular discipline.
  """
  conn = PgConnection()
  cursor = conn.cursor()

  # Active courses require both the course and the discipline to be active
  if active_only:
    which_courses = """
    and  c.course_status = 'A'
    and  c.can_schedule = 'Y'
    and  c.discipline_status = 'A'
    """
  else:
    # Always suppress courses that cannot be scheduled
    which_courses = """
    and c.can_schecule = 'Y'
    """
  if department is None:
    department_clause = ''
  else:
    department_clause = f"and c.department = '{department}'"
  if discipline is None:
    discipline_clause = ''
  else:
    discipline_clause = f"and c.discipline = '{discipline}'"
    # Course info for all courses at an institution
  institution_query = f"""
  select  c.course_id                       as course_id,
          c.offer_nbr                       as offer_nbr,
          i.name                            as institution,
          s.subject_name                    as cuny_subject,
          d.department_name                 as department,
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
          c.attributes                      as attributes

    from  cuny_courses      c,
          cuny_institutions i,
          cuny_departments  d,
          cuny_subjects     s,
          cuny_careers      cc,
          designations      rd

   where  c.institution = %s
     {which_courses}
     and  i.code = c.institution
     and  d.institution = c.institution
     and  d.department = c.department
     and  s.subject = c.cuny_subject
     and  cc.institution = c.institution
     and  cc.career = c.career
     and  rd.designation = c.designation
     {department_clause} {discipline_clause}
   order by discipline, numeric_part(catalog_number)
  """
  cursor.execute(institution_query, (institution,))

  html = ''
  for course in cursor.fetchall():
    html += format_course(course)

  cursor.close()
  conn.close()
  return html


# format_course()
# --------------------------------------------------------------------------------------------------
def format_course(course, active_only=False):
  """ Given a named tuple returned by institution_query or course_query, generate an html "catalog"
      entry for the course
  """

  # if one of the components is the primary component (it should be), make it the first one.
  components = course.components
  if len(course.components) > 1:
    components = dict(course.components)
    primary_component = [course.primary_component,
                         components.pop(course.primary_component, None)]
    components = [[component, components[component]] for component in components.keys()]
    components.insert(0, primary_component)
  component_str = ', '.join([f'{component[1]} hr {component[0].lower()}'
                            for component in components])
  if math.isclose(course.min_credits, course.max_credits):
    credits_str = f'{component_str}; {course.min_credits:0.1f} cr.'
  else:
    credits_str = f'{component_str}; {course.min_credits:0.1f}–{course.max_credits:0.1f} cr'

  transfer_link = (f'https://explorer.cuny.edu/course-transfer/{course.course_id:06}/'
                   f'{course.offer_nbr}')
  title_str = f"""<a href="{transfer_link}" style="text-decoration: none;">
                  <strong>{course.discipline} {course.catalog_number}: {course.title}</strong></a>
                  <br/>Requisites: {course.requisites}"""
  properties_str = f"""(<em>{course.career}; {course.cuny_subject}; {course.designation};
                   {', '.join(course.attributes.split(';'))}</em>)"""
  if course.course_id in cross_listed:
    # For cross-listed courses, it’s normal for the cuny_subject and requisites to change across
    # members of the group.
    # But it would be an error for career, requisites, description, designation, etc. to vary, so
    # we assume they don’t. (There are two known cases of career errors, which OUR is correcting
    # as we speak. There are no observed  errors of the other types.)
    # There is no way to get a different attributes list, because those depend only on course_id.
    title_str += '<br/>Cross-listed with:'
    conn = PgConnection()
    cursor = conn.cursor()
    cursor.execute("""
        select c.discipline, c.catalog_number, c.title,
          cc. description as career, s.subject_name as cuny_subject,
          c.designation, c.requisites, c.attributes
        from cuny_courses c, cuny_subjects s, cuny_careers cc
        where course_id = %s
        and offer_nbr != %s
        and cc.career = c.career
        and  cc.institution = c.institution
        and s.subject = c.cuny_subject
        order by discipline, catalog_number
        """, (course.course_id, course.offer_nbr))
    for cross_list in cursor.fetchall():
      title_str += f"""<br/>
      <strong>{cross_list.discipline} {cross_list.catalog_number}: {cross_list.title}</strong>
      (<em>{cross_list.career}, {cross_list.cuny_subject}, {cross_list.attributes}</em>)
      <br/>Requisites: {cross_list.requisites}
      """
    cursor.close()
    conn.close()

  note = ''
  if not active_only:
    if course.course_status != 'A':
      note = '<div class="warning"><strong>Note:</strong> Course is not active in CUNYfirst</div>'

  hover_text = f'course id: {course.course_id:06}.{course.offer_nbr}; click for transfer info'
  html = f"""
  <p class="catalog-entry" title="{hover_text}">{title_str}
    <br/>{credits_str}
    <br/>{course.description}
    <br/>{properties_str}
  </p>
  {note}
  """
  return html


def course_search(search_str, include_inactive=False, debug=False):
  """ Parse search string to get institution, discipline, and catalog_number, then find all matching
      courses and return an array of catalog entries.
      Search strings by example
        qns csci *  All CSCI courses at QC
        * csci 101 CSCI-101 at any college
        QNS01 CSCI101 CSCI 101 at QC
        QNS csci-101  CSCI 100 at QC
  """
  if debug:
    print(f'\n*** couirse_search("{search_str}", {include_inactive})')
  parts = search_str.split()
  if len(parts) < 2 or len(parts) > 3:
    raise ValueError('invalid search string')
  institution = parts[0]
  if len(parts) == 2:
    discipline, catalog_number = re.match(r'^\s*([a-z]+)-?(.+)\s*$', parts[1], re.I).groups()
  else:
    discipline, catalog_number = parts[1], parts[2]

  catalog_number = re.match(r'^\s*(\*|[\d\.]+)\D*$', catalog_number).group(1)

  if include_inactive:
    status_str = "course_status = 'A' or course_status = 'I'"
  else:
    status_str = "course_status = 'A' and can_schedule = 'Y'"

  if institution != '*':
    institution_str = f"and institution ~* '{institution}'"
  else:
    institution_str = ''

  if catalog_number != '*':
    under = float(catalog_number) - 0.5
    over = under + 1.0
    cat_num_str = """and numeric_part(catalog_number) > {} and numeric_part(catalog_number) < {}
                  """.format(under, over)
  else:
    cat_num_str = ''

  query = f"""
    select course_id, offer_nbr, course_status, institution, discipline, catalog_number
    from cuny_courses
    where {status_str}
    {institution_str}
    and discipline ~* %s
    {cat_num_str}
    """
  conn = PgConnection()
  cursor = conn.cursor()
  cursor.execute(query, (discipline, ))
  return_list = []
  for row in cursor.fetchall():
    return_list.append(lookup_course(row.course_id, offer_nbr=row.offer_nbr)[1])
  conn.close()
  return json.dumps(return_list)


# Unit Test
# -------------------------------------------------------------------------------------------------
if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('-d', '--debug', action='store_true')
  parser.add_argument('-i', '--institution')
  parser.add_argument('-c', '--course')
  parser.add_argument('-s', '--search_string')
  args = parser.parse_args()

  if args.institution:
    print(args.institution)
    exit()
    print(lookup_courses(args.institution))
  elif args.course:
    print(lookup_course(int(args.course)))
  elif args.search_string:
    print(course_search(args.search_string))
  else:
    print("Specify either an institution or a course_id")
