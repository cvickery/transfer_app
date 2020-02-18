#! /usr/bin/env python3

import logging
import inspect
from datetime import datetime
from pprint import pprint
from typing import List, Set, Dict, Tuple, Optional, Union

import argparse
import sys
import os
from io import StringIO
import re

from collections import namedtuple
from enum import Enum

from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener

from .ReqBlockLexer import ReqBlockLexer
from .ReqBlockParser import ReqBlockParser
from .ReqBlockListener import ReqBlockListener

from pgconnection import PgConnection

from closeable_objects import dict2html, items2html
from templates import *

DEBUG = os.getenv('DEBUG_PARSER')

if not os.getenv('HEROKU'):
  logging.basicConfig(filename='Logs/antlr.log',
                      format='%(asctime)s %(message)s',
                      level=logging.DEBUG)

Requirement = namedtuple('Requirement', 'keyword, value, text, course')

trans_dict: Dict[int, None] = dict()
for c in range(13, 31):
  trans_dict[c] = None

trans_table = str.maketrans(trans_dict)

# Create dict of known colleges
colleges = dict()
conn = PgConnection()
cursor = conn.cursor()
cursor.execute('select code, name from cuny_institutions')
for row in cursor.fetchall():
  colleges[row.code] = row.name
conn.close()


def format_catalog_years(period_start: str, period_stop: str) -> str:
  """ Just the range of years covered, not whether grad/undergrad
  """
  first = period_start[0:4]
  if period_stop == '99999999':
    last = 'until Now'
  else:
    last = f'through {period_stop[5:9]}'
  return f'{first} {last}'


def classes_or_credits(ctx) -> str:
  """
  """
  if DEBUG:
    print('classes_or_credits()', file=sys.stderr)
  classes_credits = ctx.CREDITS()
  if classes_credits is None:
    classes_credits = ctx.CLASSES()
  return str(classes_credits).lower()


def build_course_list(institution, ctx) -> list:
  """ INFROM? class_item (AND class_item)*
      INFROM? class_item (OR class_item)*
  """
  if DEBUG:
    print('build_course_list()', file=sys.stderr)
  course_list: list = []
  if ctx is None:
    return course_list
  # if ctx.INFROM():
  #   print(f'INFROM: {ctx.INFROM()}')
  for class_item in ctx.class_item():
    if class_item.SYMBOL():
      display_discipline = str(class_item.SYMBOL())
      search_discipline = display_discipline
    if class_item.WILDSYMBOL():
      display_discipline = str(class_item.WILDSYMBOL())
      search_discipline = display_discipline.replace('@', '.*')
    if class_item.NUMBER():
      display_number = str(class_item.NUMBER())
      search_number = f"catalog_number = '{display_number}'"
    if class_item.RANGE():
      display_number = str(class_item.RANGE())
      low, high = display_number.split(':')
      search_number = f""" numeric_part(catalog_number) >= {float(low)} and
                           numeric_part(catalog_number) <' {float(high)}'
                      """
    if class_item.WILDNUMBER():
      display_number = str(class_item.wildnumber)
      search_number = f"catalog_number ~ '{display_number.replace('@', '.*')}'"
    course_query = f"""
                      select institution, course_id, offer_nbr, discipline, catalog_number, title,
                             description, course_status, max_credits, designation, attributes
                        from cuny_courses
                       where institution ~* '{institution}'
                         and discipline ~ '{search_discipline}'
                         and {search_number}
                    """
    conn = PgConnection()
    cursor = conn.cursor()
    cursor.execute(course_query)
    print(f'{institution} {search_discipline} {search_number} returned {cursor.rowcount} rows', file=sys.stderr)
    # Convert generator to list.
    details = [row for row in cursor.fetchall()]
    course_list.append({'display': f'{display_discipline} {display_number}',
                        'info': details})
    conn.close()
  if DEBUG:
    print(f'return list len {len(course_list)}', file=sys.stderr)
  return course_list


def course_list2html(course_list: dict):
  """ Look up all the courses in course_list, and return their catalog entries as HTML divs
  """
  all_blanket = True
  all_writing = True

  return_list = []
  for course in course_list:
    print(course)
    for info in course['info']:
      if info.course_status == 'A' and 'WRIC' not in info.attributes:
        all_writing = False
      if info.course_status == 'A' and info.max_credits > 0 and 'BKCR' not in info.attributes:
        all_blanket = False
      return_list.append(f"""
                  <div title="{info.course_id}:{info.offer_nbr}">
                    {info.discipline} {info.catalog_number} {info.title}
                    <br>
                    {info.description}
                    <br>
                    {info.designation} {info.attributes}
                    {'<span class="error">Inactive Course</span>' * (info.course_status == 'I')}
                  </div>
              """)
  attributes = []
  if all_blanket:
    attributes.append('Blanket Credit')
  if all_writing:
    attributes.append('Writing Intensive')

  return attributes, return_list


class ScribeSection(Enum):
  """ Keep track of which section of a Scribe Block is being processed.
  """
  NONE = 0
  HEAD = 1
  BODY = 2


# Class ReqBlockInterpreter
# =================================================================================================
class ReqBlockInterpreter(ReqBlockListener):
  def __init__(self, institution, block_type, block_value, title, period_start, period_stop,
               requirement_text):
    if DEBUG:
      print(f'*** ReqBlockInterpreter({institution}, {block_type}, {block_value})', file=sys.stderr)
    self.institution = institution
    self.block_type = block_type
    self.block_type_str = block_type.lower().replace('conc', 'concentration')
    self.block_value = block_value
    self.title = title
    self.period_start = period_start
    self.period_stop = period_stop
    self.institution = colleges[institution]
    self.requirement_text = requirement_text
    self.scribe_section = ScribeSection.NONE
    self.sections = [[], [], []]  # NONE, HEAD, BODY

  @property
  def html(self):
    len_empty = len(self.sections[ScribeSection.NONE.value])
    assert len_empty == 0, (
        f'ERROR: Scribe Block Section {ScribeSection.NONE.name} has'
        f'{len_empty} item{"" if len_empty == 1 else "s"} instead of none.')
    html_body = f"""
<h1>{self.institution} {self.title}</h1>
<p>Requirements for Catalog Years
{format_catalog_years(self.period_start, self.period_stop)}
</p>
<section>
  <h1 class="closer">Degreeworks Code</h1>
  <div>
    <hr>
    <pre>{self.requirement_text.replace('<','&lt;')}</pre>
  </div>
</section>
<section>
  <h1 class="closer">Interpretation</h1>
  <div>
    <hr>
    {items2html(self.sections[ScribeSection.HEAD.value], 'Head Item')}
    {items2html(self.sections[ScribeSection.BODY.value], 'Body Item')}
  </div>
</section
"""

    return html_body

  def enterHead(self, ctx):
    if DEBUG:
      print('enterHead()', file=sys.stderr)
    self.scribe_section = ScribeSection.HEAD

  def enterBody(self, ctx):
    if DEBUG:
      print('enterBody()', file=sys.stderr)
    self.scribe_section = ScribeSection.BODY

  def enterMinres(self, ctx):
    """ MINRES NUMBER (CREDITS | CLASSES)
    """
    if DEBUG:
      print('enterMinres()', file=sys.stderr)
    classes_credits = classes_or_credits(ctx)
    # print(inspect.getmembers(ctx))
    if float(str(ctx.NUMBER())) == 1:
      classes_credits = classes_credits.strip('es')
    self.sections[self.scribe_section.value].append(
        Requirement('minres',
                    f'{ctx.NUMBER()} {classes_credits}',
                    f'At least {ctx.NUMBER()} {str(classes_credits).lower()} '
                    f'must be completed in residency.',
                    None))

  def enterNumcredits(self, ctx):
    """ (NUMBER | RANGE) CREDITS (and_courses | or_courses)?
    """
    if DEBUG:
      print('enterNumcredits()', file=sys.stderr)
    text = f'This {self.block_type_str} requires '
    if ctx.NUMBER() is not None:
      text += f'{ctx.NUMBER()} credits'
    elif ctx.RANGE() is not None:
      low, high = str(ctx.RANGE()).split(':')
      text += f'between {low} and {high} credits'
    else:
      text += f'an <span class="error">unknown</span> number of credits'

    course_list = None
    if ctx.and_courses() is not None:
      course_list = build_course_list(self.institution, ctx.and_courses())
      list_quantifier = 'all'
    if ctx.or_courses() is not None:
      course_list = build_course_list(self.institution, ctx.or_courses())
      list_quantifier = 'any'

    if course_list is None:
      text += '.'
      courses = None
    else:
      len_list = len(course_list)
      attributes, html_list = course_list2html(course_list)
      if len_list == 1:
        preamble = f' in {list_quantifier}'
        courses = html_list[0]
      else:
        preamble = f' in {list_quantifier} of these {len_list} {" and ".join(attributes)} courses:'
        courses = html_list
      text += f' {preamble} '
    self.sections[self.scribe_section.value].append(
        Requirement('credits',
                    f'{ctx.NUMBER()} credits',
                    f'{text}',
                    courses))

  def enterMaxcredits(self, ctx):
    """ MAXCREDITS NUMBER (and_courses | or_courses)
    """
    if DEBUG:
      print('enterMaxcredits()', file=sys.stderr)
    limit = f'a maximum of {ctx.NUMBER()}'
    if ctx.NUMBER() == '0':
      limit = 'zero'
    text = f'This {self.block_type} allows {limit} credits'
    course_list = None
    if ctx.and_courses() is not None:
      course_list = build_course_list(self.institution, ctx.and_courses())
      list_quantifier = 'all'
    if ctx.or_courses() is not None:
      course_list = build_course_list(self.institution, ctx.or_courses())
      list_quantifier = 'any'

    if course_list is None:
      text += '.'
      courses = None
    else:
      len_list = len(course_list)
      attributes, html_list = course_list2html(course_list)
      assert len_list == len(html_list), f'{len_list} is not {len(html_list)}'
      if len_list == 1:
        preamble = f' in {list_quantifier}'
        courses = html_list[0]
      else:
        preamble = f' in {list_quantifier} of these {len_list} {" and ".join(attributes)} courses:'
        courses = html_list
      text += f' {preamble} '
    self.sections[self.scribe_section.value].append(
        Requirement('maxcredits',
                    f'{ctx.NUMBER()} credits',
                    f'{text}',
                    courses))

  def enterMaxclasses(self, ctx):
    """ MAXCLASSES NUMBER (and_courses | or_courses)
    """
    if DEBUG:
      print('enterMaxclasses()', file=sys.stderr)
    num_classes = int(str(ctx.NUMBER()))
    limit = f'no more than {num_classes}'
    if num_classes == 0:
      limit = 'no'
    print(f'This {self.block_type} allows {limit} class{"es" * (num_classes != 1)} from ', end='')
    if ctx.and_courses() is not None:
      build_course_list(ctx.and_courses())
    if ctx.and_courses() is not None:
      print(course_list2html(build_course_list(self.institution, ctx.and_courses())), end='')
    if ctx.or_courses() is not None:
      print(course_list2html(build_course_list(self.institution, ctx.or_courses())), end='')
    print()

  def enterMaxpassfail(self, ctx):
    """ MAXPASSFAIL NUMBER (CREDITS | CLASSES) (TAG '=' SYMBOL)?
    """
    if DEBUG:
      print('enterMaxpassfail()', file=sys.stderr)
    num = int(str(ctx.NUMBER()))
    limit = f'no more than {ctx.NUMBER()}'
    if num == 0:
      limit = 'no'
    which = classes_or_credits(ctx)
    if num == 1:
      which = which[0:-1].strip('e')
    print(f'<p>This {self.block_type} allows {limit} {which} to be taken Pass/Fail!</p>')


# Class DGW_Logger
# =================================================================================================
class DGW_Logger(ErrorListener):

  def __init__(self, institution, block_type, block_value, period_stop):
    self.block = f'{institution} {block_type} {block_value} {period_stop}'

  def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
    logging.debug(f'{self.block} {type(recognizer).__name__} '
                  f'Syntax {line}:{column} {msg}')

  def reportAmbiguity(self, recognizer, dfa, startIndex, stopIndex, exact, ambigAlts, configs):
    logging.debug(f'{self.block}: {type(recognizer).__name__} '
                  f'Ambiguity {startIndex}:{stopIndex} {exact} ({ambigAlts}) {configs}')

  def reportAttemptingFullContext(self, recognizer, dfa, startIndex, stopIndex,
                                  conflictingAlts, configs):
    logging.debug(f' {self.block}: {type(recognizer).__name__} '
                  f'FullContext {dfa} {startIndex}:{stopIndex} ({conflictingAlts}) {configs}')

  def reportContextSensitivity(self, recognizer, dfa, startIndex, stopIndex, prediction, configs):
    logging.debug(f' {self.block}: {type(recognizer).__name__} '
                  f'ContextSensitivity {dfa} {startIndex}:{stopIndex} ({prediction}) {configs}')


# dgw_parser()
# =================================================================================================
def dgw_parser(institution, block_type, block_value, period='current'):
  """  Creates a ReqBlockInterpreter, which will include a json representation of requirements.
       For now, it returns an html string telling what it was able to extract from the requirement
       text.
       The period argument can be 'current', 'latest', or 'all', which will be picked out of the
       result set for 'all'
  """
  if DEBUG:
    print(f'*** dgw_parser({institution}, {block_type}, {block_value}. {period})')
  conn = PgConnection()
  cursor = conn.cursor()
  query = """
    select requirement_id, title, period_start, period_stop, requirement_text
    from requirement_blocks
    where institution ~* %s
      and block_type = %s
      and block_value = %s
    order by period_stop desc
  """
  cursor.execute(query, (institution, block_type.upper(), block_value.upper()))
  if cursor.rowcount == 0:
    # This is a bug, not an error
    return f'<h1 class="error">No Requirements Found</h1><p>{cursor.query}</p>'
  return_html = ''
  for row in cursor.fetchall():
    if period == 'current' and row.period_stop != '99999999':
      return f"""<h1 class="error">“{row.title}” is not a currently offered {block_type}
                 at {institution}.</h1>
              """
    requirement_text = row.requirement_text\
                          .translate(trans_table)\
                          .strip('"')\
                          .replace('\\r', '\r')\
                          .replace('\\n', '\n') + '\n'
    dgw_logger = DGW_Logger(institution, block_type, block_value, row.period_stop)
    # Unable to get Antlr to ignore cruft before BEGIN and after END. so, reluctantly, removing the
    # cruft here in order to get on with parsing.
    match = re.search(r'.*?(BEGIN.*?END\.).*', requirement_text, re.I | re.S)
    if match is None:
      raise ValueError(f'BEGIN...;...END. not found:\n{requirement_text}')
    input_stream = InputStream(match.group(1))
    lexer = ReqBlockLexer(input_stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(dgw_logger)
    token_stream = CommonTokenStream(lexer)
    parser = ReqBlockParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(dgw_logger)
    interpreter = ReqBlockInterpreter(institution,
                                      block_type,
                                      block_value,
                                      row.title,
                                      row.period_start,
                                      row.period_stop,
                                      requirement_text)
    try:
      walker = ParseTreeWalker()
      tree = parser.req_block()
      walker.walk(interpreter, tree)
      return_html += interpreter.html
    except Exception as e:
      return_html += f"""
                        <p class="error">Currently unable to interpret this block.</p>
                        <p>Internal Error Message: “<em>{e}</em>”</p>
                      """

    if period == 'current' or period == 'latest':
      break
  conn.close()
  return return_html


if __name__ == '__main__':

  # Command line args
  parser = argparse.ArgumentParser(description='Test DGW Parser')
  parser.add_argument('-d', '--debug', action='store_true', default=False)
  parser.add_argument('-f', '--format')
  parser.add_argument('-i', '--institutions', nargs='*', default=['QNS01'])
  parser.add_argument('-t', '--block_types', nargs='+', default=['MAJOR'])
  parser.add_argument('-v', '--block_values', nargs='+', default=['CSCI-BS'])
  parser.add_argument('-a', '--development', action='store_true', default=False)

  # Parse args and handle default list of institutions
  args = parser.parse_args()

  # Get the top-level requirements to examine: college, block-type, and/or block value
  conn = PgConnection()
  cursor = conn.cursor()

  query = """
      select requirement_id, title, requirement_text
      from requirement_blocks
      where institution = %s
        and block_type = %s
        and block_value = %s
        and period_stop = '99999999'
  """
  for institution in args.institutions:
    institution = institution.upper() + ('01' * (len(institution) == 3))
    for block_type in args.block_types:
      for block_value in args.block_values:
        if args.debug:
          print(institution, block_type, block_value)
        print(dgw_parser(institution, block_type, block_value))
  conn.close()
