import json
from json import JSONEncoder
import re

from datetime import datetime


class Requirements():
  """ Representation of the requirements for an academic program for one range of Catalog Years.

      The constructor takes a text description in Degreeworks Scribe format, which is stored as the
      "scribe_text" member. The parsed information is available in the "json" and "html" members.
      The _str_() method returns a plain text version.

      Fields:
        years       Catalog Year(s)
        credits     Total Credits
        limit       Transfer Credits Allowed
        courses     Required Courses
        notes       Notes
        scribe_text Raw requirements text in scribe format

  """

  def __init__(self, requirement_text, period_start, period_stop,
               total_credits=0.0,
               transfer_limit=0.0,
               ):
    self.scribe_text = requirement_text
    self.catalogs = Catalogs(period_start, period_stop)
    self.years = list(range(self.catalogs.first_academic_year.year,
                            self.catalogs.last_academic_year.year + 1))
    self.total_credits = total_credits
    self.transfer_limit = transfer_limit
    self.courses = {}
    self.notes = ''
    self.comments = []
    self.text = []
    ignore = [';',
              '(clob)',
              'display',
              'nonexclusive',
              'proxy-advice',
              'sharewith',
              ]
    lines = requirement_text.split('\n')
    for line in lines:
      if line.startswith('#') or \
         line.startswith('/') or \
         line.lower().startswith('log') or \
         line.lower().startswith('remark'):
        self.comments.append(line)
      else:
        tokens = line.split()
        if len(tokens) > 0 and tokens[0].lower() not in ignore:
          self.text.append(line)

  def __str__(self):
    return '\n'.join(self.__dict__['text'])

  def json(self):
    return json.dumps(self.__dict__, default=lambda x: x.__dict__)

  def html(self):
    num_catalogs = len(self.catalogs.which_catalogs)
    if num_catalogs == 0:
      catalog_str = 'College catalog.'
    elif num_catalogs == 1:
      catalog_str = f'{self.catalogs.which_catalogs[0]} Catalog.'
    else:
      catalog_str = f'{self.catalogs.which_catalogs[0]} and '
      f'{self.catalogs.which_catalogs[1]} Catalogs.'
    years_str = ', '.join([f'{year}' for year in self.years])
    k = years_str.rfind(',')
    if k > 0:
      k += 1
      years_str = years_str[:k] + ' and' + years_str[k:]
    if self.catalogs.first_academic_year != self.catalogs.last_academic_year:
      suffix = 's'
    else:
      suffix = ''
    returnVal = f"""
                <h2>Requirements for Catalog Year{suffix} {str(self.catalogs)}</h2>
                <p>Academic years starting in the fall of {years_str}</p>
                <p>This program appears in the {catalog_str}</p>
                """
    for line in self.text:
      returnVal += f'<p>{line}</p>'
    return returnVal


class AcademicYear:
  """ This is a helper class for representing one academic year as a string.
      Academic years run from September through the following August.
      The sting will be either CCYY-YY or CCYY-CCYYY or Now
  """
  def __init__(self, century_1=None, year_1=None, century_2=None, year_2=None):
    """ Academic_Year constructor. Second year must be one greater than the first.
        if no args, the year is “Now”
    """
    if century_1 is None:
      self.is_now = True
      now = datetime.now()
      # The current academic year began last year if it is now Jan-Aug.
      if now.month < 9:
        self.year = now.year - 1
      else:
        self.year = now.year
    else:
      self.is_now = False
      self.century_1 = int(century_1)
      self.year_1 = int(year_1)
      self.century_2 = int(century_2)
      self.year_2 = int(year_2)
      self.year = 100 * self.century_1 + self.year_1
      if (100 * self.century_1 + self.year_1 + 1) != (100 * self.century_2 + self.year_2):
        raise ValueError(f'{100 * self.century_1 + self.year_1}, '
                         f'{100 * self.century_2 + self.year_2} is not a valid pair of years')

  def __str__(self):
    if self.is_now:
      return 'Now'
    else:
      if self.century_1 != self.century_2:
        return f'{self.century_1}{self.year_1:02}-{self.century_2}{self.year_2:02}'
      else:
        return f'{self.century_1}{self.year_1:02}-{self.year_2:02}'


class Catalogs():
  def __init__(self, period_start, period_stop):
    """ Represents a range of catalog years and which catalogs (graduate, undergraduate, both, or
        unspecified) are involved. When a student starts a program, the catalog year tells what the
        requirements are at that time.

    """
    self.which_catalogs = []  # Serializable
    which_catalogs = set()  # Not serializable
    self.first_academic_year = None
    self.last_academic_year = None

    m_start = re.search(r'(19|20)(\d\d)-?(19|20)(\d\d)([UG]?)', period_start)
    if m_start is not None:
      century_1, year_1, century_2, year_2, catalog = m_start.groups()
      try:
        self.first_academic_year = AcademicYear(century_1, year_1, century_2, year_2)
      except ValueError as e:
        self.first_academic_year = f'Unknown: {e}.'
      self.first_year = (century_1 * 100) + year_1
      if catalog == 'U':
        which_catalogs.add('Undergraduate')
      if catalog == 'G':
        which_catalogs.add('Graduate')

    if re.search(r'9999+', period_stop):
      self.last_academic_year = AcademicYear()
    else:
      m_stop = re.search(r'(19|20)(\d\d)-?(19|20)(\d\d)([UG]?)', period_stop)
      if m_stop is not None:
        century_1, year_1, century_2, year_2, catalog = m_stop.groups()
        try:
          self.last_academic_year = AcademicYear(century_1, year_1, century_2, year_2)
        except ValueError as e:
          self.last_academic_year = f'Unknown: {e}.'
        self.last_year = (century_1 * 100) + year_1
        if catalog == 'U':
          which_catalogs.add('Undergraduate')
        if catalog == 'G':
          which_catalogs.add('Graduate')
    self.which_catalogs = sorted(list(which_catalogs), reverse=True)

  def __str__(self):
    if self.first_academic_year != self.last_academic_year:
      return f'{self.first_academic_year} through {self.last_academic_year}'
    else:
      return f'{self.first_academic_year}'
