import sqlite3
import re

# CUNYCourse
# -------------------------------------------------------------------------------------------------
class CUNYCourse:
  """ Catalog and related info for a CUNYfirst course.
  """
  def __init__(self, course_id):
    """ Get complete information for a course from cuny_catalog.db.
    """
    m = re.search('\s*(\d+)\s*$', str(course_id))
    if m == None:
      raise ValueError('"{}" is not a valid course_id'.format(course_id))
    self.course_id = m.group(1)

    conn = sqlite3.connect('static/db/cuny_catalog.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("select * from courses where course_id = '{}'".format(course_id))
    course = c.fetchone()
    if course:
      c.execute("select * from cuny_subjects where area = '{}'".format(course['cuny_subject']))
      cuny_subject = c.fetchone()[1]

      c.execute("""
                select description from careers where institution = '{}' and career = '{}'
                """.format(course['institution'], course['career']))
      career = c.fetchone()[0]

      c.execute("""
                select description from designations where designation = '{}'
                """.format(course['designation']))
      designation = c.fetchone()[0]

      self.is_active = course['course_status'] == 'A'

      c.execute("select name from institutions where code = '{}'".format(course['institution']))
      institution = c.fetchone()[0]
      self.institution = institution

      c.execute("""
                select a.attribute_name, a.attribute_value, a.description
                from attributes a, course_attributes c
                where c.course_id = {}
                  and c.name = a.attribute_name
                  and c.value = a.attribute_value
                """.format(course_id))
      the_attributes = [row[2] for row in c.fetchall()]
      self.attributes = ''
      if the_attributes == None or len(the_attributes) == 0:
        pass
      else:
        for attribute in the_attributes:
          self.attributes += '<div class="catalog-entry"><strong>Attribute:</strong> {}</div>\n'.format(attribute)

      self.html = """
      <p class="catalog-entry"><strong>{} {}: {}</strong> (<em>{}; {}</em>)<br/>
      {:0.1f}hr; {:0.1f}cr; Requisites: <em>{}</em><br/>{} (<em>{}</em>)</p>{}
      """.format(course['discipline'],
                 course['number'].strip(),
                 course['title'],
                 career,
                 cuny_subject,
                 float(course['hours']),
                 float(course['credits']),
                 course['requisites'],
                 course['description'],
                 designation,
                 self.attributes)

    else:
      self.html = '<p class="catalog-entry">{} Not in CUNY Catalog</p>'.format(course_id)
      self.is_active = False
      self.institution = 'No Institution'

  def __str__(self):
    return self.html

  def course_id(self):
    return self.course_id
  def is_active(self):
    return self.is_active
  def institution(self):
    return self.institution
