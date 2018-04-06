from pgconnection import pgconnection
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

    conn = pgconnection('dbname=cuny_courses')
    cursor = conn.cursor()
    cursor.execute("select * from courses where course_id = '{}'".format(course_id))
    course = cursor.fetchone()
    if course:
      self.exists = True
      cursor.execute("""
                select * from cuny_subjects where subject = '{}'""".format(course['cuny_subject']))
      cuny_subject = cursor.fetchone()[1]

      cursor.execute("""
                select description from cuny_careers where institution = '{}' and career = '{}'
                """.format(course['institution'], course['career']))
      career = cursor.fetchone()[0]

      cursor.execute("""
                select description from designations where designation = '{}'
                """.format(course['designation']))
      designation = cursor.fetchone()[0]

      cursor.execute("""
                select description from cuny_departments where department = '{}'
                """.format(course['department']))
      department = cursor.fetchone()[0]
      self.department = department

      self.is_active = course['course_status'] == 'A'


      cursor.execute("select name from institutions where code = '{}'".format(course['institution']))
      institution = cursor.fetchone()[0]
      self.institution = institution

      cursor.execute("""
                select a.attribute_name, a.attribute_value, a.description
                from attributes a, course_attributes c
                where c.course_id = {}
                  and c.name = a.attribute_name
                  and c.value = a.attribute_value
                """.format(course_id))
      the_attributes = [row[2] for row in cursor.fetchall()]
      self.attributes = ''
      if the_attributes == None or len(the_attributes) == 0:
        pass
      else:
        for attribute in the_attributes:
          self.attributes += """
            <div class="catalog-entry"><strong>Attribute:</strong> {}</div>\n""".format(attribute)
      cursor.close()
      conn.close()
      self.discipline = course['discipline']
      self.catalog_number = course['catalog_number'].strip()
      self.title = course['title']
      self.html = """
      <p class="catalog-entry" title="course id: {}"><strong>{} {}: {}</strong> (<em>{}; {}</em>)
      <br/>
      {:0.1f}hr; {:0.1f}cr; Requisites: <em>{}</em><br/>{} (<em>{}</em>)</p>{}
      """.format(self.course_id,
                 self.discipline,
                 self.catalog_number,
                 self.title,
                 career,
                 cuny_subject,
                 float(course['hours']),
                 float(course['credits']),
                 course['requisites'],
                 course['description'],
                 designation,
                 self.attributes)
      self.title_str = """course_id {}: {} {} {} {:0.1f}hr;{:0.1f}cr""".format(course['course_id'],
                                                              course['discipline'],
                                                              course['catalog_number'].strip(),
                                                              course['title'],
                                                              float(course['hours']),
                                                              float(course['credits']))

    else:
      self.exists = False
      self.html = '<p class="catalog-entry">{} Not in CUNY Catalog</p>'.format(course_id)
      self.title_str = 'course_id {}: Not in CUNY Catalog'.format(course_id)
      self.is_active = False
      self.institution = 'No Institution'
      self.department = 'No Department'
      self.discipline = 'No Discipline'
      self.catalog_number = '###'
      self.title = 'No Title'

  def __str__(self):
    return self.html

  def course_id(self):
    return self.course_id
  def is_active(self):
    return self.is_active
  def institution(self):
    return self.institution
  def department(self):
    return self.department
