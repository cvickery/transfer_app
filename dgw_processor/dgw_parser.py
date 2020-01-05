#! /usr/local/bin/python3

import logging
from datetime import datetime
from pprint import pprint
from typing import List, Set, Dict, Tuple, Optional, Union

import argparse
import sys
import os
from io import StringIO

from collections import namedtuple

from antlr4 import *
from antlr4.error.ErrorListener import ErrorListener

from .ReqBlockLexer import ReqBlockLexer
from .ReqBlockParser import ReqBlockParser
from .ReqBlockListener import ReqBlockListener
from .pgconnection import pgconnection

if not os.getenv('HEROKU'):
  logging.basicConfig(filename='Logs/antlr.log',
                      format='%(asctime)s %(message)s',
                      level=logging.DEBUG)

trans_dict: Dict[int, None] = dict()
for c in range(13, 31):
  trans_dict[c] = None

trans_table = str.maketrans(trans_dict)

# Create dict of known colleges
colleges = dict()
course_conn = pgconnection()
course_cursor = course_conn.cursor()
course_cursor.execute('select code, name from institutions')
for row in course_cursor.fetchall():
  colleges[row.code] = row.name


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
  classes_credits = ctx.CREDITS()
  if classes_credits is None:
    classes_credits = ctx.CLASSES()
  return str(classes_credits).lower()


def build_course_list(institution, ctx) -> list:
  """ INFROM? class_item (AND class_item)*
      INFROM? class_item (OR class_item)*
  """
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
                             course_status, max_credits, designation, attributes
                        from courses
                       where institution ~* '{institution}'
                         and discipline ~ '{search_discipline}'
                         and {search_number}
                    """
    course_cursor.execute(course_query)
    # Convert generator to list.
    details = [row for row in course_cursor.fetchall()]
    course_list.append({'display': f'{display_discipline} {display_number}',
                        'info': details})
  return course_list


def course_list_to_html(course_list: dict):
  """ Generate a details element that has the number of courses as the summary, and the catalog
      descriptions when opened. The total number of courses is the sum of each group of courses.
  """
  num_courses = 0
  all_blanket = True
  all_writing = True

  html = '<details style="margin-left:1em;">'
  for course in course_list:
    for info in course['info']:
      num_courses += 1
      if info.course_status == 'A' and 'WRIC' not in info.attributes:
        all_writing = False
      if info.course_status == 'A' and info.max_credits > 0 and 'BKCR' not in info.attributes:
        all_blanket = False
      html += f"""
                <p title="{info.course_id}:{info.offer_nbr}">
                  {info.discipline} {info.catalog_number} {info.title}
                  <br>
                  {info.designation} {info.attributes}
                  {'<span class="error">Inactive Course</span>' * (info.course_status == 'I')}
                </p>
              """
  attributes = ''
  if all_blanket:
    attributes = 'Blanket Credit '
  if all_writing:
    attributes += 'Writing Intensive '
  summary = f'<summary> these {num_courses} {attributes} courses.</summary>'
  if num_courses == 1:
    summary = f'<summary> this {attributes} course.</summary>'
  return html + summary + '</details>'


# Class ReqBlockInterpreter
# =================================================================================================
class ReqBlockInterpreter(ReqBlockListener):
  def __init__(self, institution, block_type, block_value, title, period_start, period_stop,
               requirement_text):
    self.institution = institution
    self.block_type = block_type.lower()
    self.block_value = block_value
    self.title = title
    self.period_start = period_start
    self.period_stop = period_stop
    self.college_name = colleges[institution]
    self.html = f"""<h1>{self.college_name} {self.title}</h1>
                    <p>Requirements for Catalog Years
                    {format_catalog_years(period_start, period_stop)}
                    </p>
                    <details><summary>Degreeworks Code</summary><hr>
                      <pre>{requirement_text}</pre>
                    </details>
                    <div class="requirements">
                    <h2>Description (Incomplete)</h2>
                 """
    if self.block_type == 'conc':
      self.block_type = 'concentration'

  def enterMinres(self, ctx):
    """ MINRES NUMBER (CREDITS | CLASSES)
    """
    classes_credits = classes_or_credits(ctx)
    # print(inspect.getmembers(ctx))
    if float(str(ctx.NUMBER())) == 1:
      classes_credits = classes_credits.strip('es')
    self.html += (f'<p>At least {ctx.NUMBER()} {str(classes_credits).lower()} '
                  f'must be completed in residency.</p>')

  def enterNumcredits(self, ctx):
    """ (NUMBER | RANGE) CREDITS (and_courses | or_courses)?
    """
    if ctx.NUMBER() is not None:
      self.html += (f'<p>This {self.block_type} requires {ctx.NUMBER()} credits.')
    elif ctx.RANGE() is not None:
       low, high = str(ctx.RANGE()).split(':')
       self.html += (f'<p>This {self.block_type} requires between {low} and {high} credits.')
    else:
      self.html += (f'<p class="warning">This {self.block_type} requires an '
                    f'<strong>unknown</strong> number of credits.')
    if ctx.and_courses() is not None:
      self.html += course_list_to_html(build_course_list(self.institution, ctx.and_courses()))
    if ctx.or_courses() is not None:
      self.html += course_list_to_html(build_course_list(self.institution, ctx.or_courses()))
    self.html += '</p>'

  def enterMaxcredits(self, ctx):
    """ MAXCREDITS NUMBER (and_courses | or_courses)
    """
    limit_type = 'a maximum of'
    if ctx.NUMBER() == '0':
      limit_type = 'zero'
    self.html += (f'<p>This {self.block_type} allows {limit_type} of {ctx.NUMBER()} credits in ')
    if ctx.and_courses() is not None:
      self.html += course_list_to_html(build_course_list(self.institution, ctx.and_courses()))
    if ctx.or_courses() is not None:
      self.html += course_list_to_html(build_course_list(self.institution, ctx.or_courses()))
    self.html += '</p>'

  def enterMaxclasses(self, ctx):
    """ MAXCLASSES NUMBER (and_courses | or_courses)
    """
    num_classes = int(str(ctx.NUMBER()))
    limit = f'no more than {num_classes}'
    if num_classes == 0:
      limit = 'no'
    self.html += (f'<p>This {self.block_type} allows {limit} '
                  f'class{"es" * (num_classes != 1)} from ')
    if ctx.and_courses() is not None:
      build_course_list(ctx.and_courses())
    if ctx.and_courses() is not None:
      self.html += course_list_to_html(build_course_list(self.institution, ctx.and_courses()))
    if ctx.or_courses() is not None:
      self.html += course_list_to_html(build_course_list(self.institution, ctx.or_courses()))
    self.html += '</p>'

  def enterMaxpassfail(self, ctx):
    """ MAXPASSFAIL NUMBER (CREDITS | CLASSES) (TAG '=' SYMBOL)?
    """
    num = int(str(ctx.NUMBER()))
    limit = f'no more than {ctx.NUMBER()}'
    if num == 0:
      limit = 'no'
    which = classes_or_credits(ctx)
    if num == 1:
      which = which[0:-1].strip('e')
    self.html += (f'<p>This {self.block_type} allows {limit} {which} ')
    self.html += 'to be taken Pass/Fail.</p>'


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
  conn = pgconnection()
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
    return f'<h1 class="error">No Requisites Found</h1><p>{cursor.query}</p>'
  return_html = ''
  for row in cursor.fetchall():
    if period == 'current' and row.period_stop != '99999999':
      return f"""<h1 class="error">“{row.title}” is not a currently offered {interpreter.block_type}
                 at {interpreter.college_name}.</h1>
              """
    requirement_text = row.requirement_text\
                          .translate(trans_table)\
                          .strip('"')\
                          .replace('\\r', '\r')\
                          .replace('\\n', '\n') + '\n'
    dgw_logger = DGW_Logger(institution, block_type, block_value, row.period_stop)
    input_stream = InputStream(requirement_text)
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
    walker = ParseTreeWalker()
    try:
      tree = parser.req_text()
      walker.walk(interpreter, tree)
      return_html += interpreter.html + '</div>'
    except Exception as e:
      return_html += f"""
                        <p class="error">Currently unable to interpret this block.</p>
                        <p>Internal Error Message: “<em>{e}</em>”</p>
                      """

    if period == 'current' or period == 'latest':
      break
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
  conn = pgconnection()
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
