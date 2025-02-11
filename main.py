#! /usr/bin/env python3
"""Transfer Explorer: “Laboratory” app.
   Christopher Vickery
"""
import os
import psycopg
import re
import socket

import json
import csv

from datetime import datetime, timedelta, date
from pathlib import Path

from collections import namedtuple, defaultdict, Counter

from psycopg.rows import namedtuple_row
from psycopg.types.json import Json

from app_header import header
from course_info import _course_info
from course_lookup import lookup_courses, lookup_course
from course_lookup import course_attribute_rows, course_search
# from course_mappings import course_mappings_impl
import course_requirements
from find_programs import find_programs
from format_rules import format_rule, format_rule_by_key
from htmlificization import scribe_block_to_html
from plan_subplan_options import options_dict
from program_descriptions import describe, to_html
from review_rules import do_form_0, do_form_1, do_form_2, do_form_3
from reviews import process_pending
from rules_diff import diff_rules, archive_dates, available_archive_dates
from rule_history import rule_history
from sendemail import send_message
from system_status import app_available, app_unavailable, get_reason, \
    start_update_db, end_update_db, start_maintenance, end_maintenance
from top_menu import top_menu
from what_requirements import what_requirements

from flask import Flask, render_template, make_response, \
    send_file, request, jsonify, session
from flask_session import Session
from markupsafe import Markup

import redis

redis_url = 'redis://localhost'

# Uppercase variables in this module are treated as configuration keys by app.config.from_object()
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.from_url(redis_url)
PERMANENT_SESSION_LIFETIME = timedelta(days=90)
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Needed for session support
app.config.from_object(__name__)

Session(app)  # Session gets its configuration params from the app config dict.

# During local development, enable more detailed log messages from the app.
if os.getenv('DEVELOPMENT') is not None:
  DEBUG = True
else:
  DEBUG = False

# Cache db tables
with psycopg.connect('dbname=cuny_curriculum') as conn:
  with conn.cursor(row_factory=namedtuple_row) as cursor:

    # Colleges
    cursor.execute("""
    select code, prompt from cuny_institutions
    """)
    college_names = {c.code: c.prompt for c in cursor}

    # Disciplines
    cursor.execute(r"""
    select institution, discipline, discipline_name
      from cuny_disciplines
     where status = 'A'
       and cuny_subject != 'MESG'
       and discipline !~ '^\d*$'
       order by discipline
    """)
    disciplines = defaultdict(dict)
    for row in cursor:
      disciplines[row.institution][row.discipline] = f'{row.discipline_name} ({row.discipline})'

select_cuny_colleges = [f'<option value="{k}">{v}</option>' for k, v in college_names.items()]
select_cuny_colleges = '\n'.join(sorted(select_cuny_colleges))
select_college_disciplines = dict()
for college in disciplines.keys():
  select_disciplines = []
  for discipline in disciplines[college]:
    select_disciplines.append(f'<option value="{discipline}">{disciplines[college][discipline]}'
                              f'</option>')
  select_college_disciplines[college] = '\n'.join(sorted(select_disciplines))


# Overhead URIs
# =================================================================================================
@app.route('/favicon.ico')
def favicon():
  return send_file('favicon.ico', mimetype="image/x-icon")


@app.route('/image/<file_name>')
def image_file(file_name):
  return send_file('static/images/' + file_name + '.png')


# _STATUS
# -------------------------------------------------------------------------------------------------
@app.route('/_status/<command>')
def _status(command):
  """ Start/End DB Update / Maintenance
      TODO: Need to add user authentication to this.
  """

  dispatcher = {
      'start_update': start_update_db,
      'end_update': end_update_db,
      'start_maintenance': start_maintenance,
      'end_maintenance': end_maintenance,
      'check': app_available
  }

  if command in dispatcher.keys():
    current_status = dispatcher[command]()
    if current_status:
      return top_menu()
    else:
      return render_template('app_unavailable.html', result=Markup(get_reason()))
  else:
    return ''


# date2str()
# --------------------------------------------------------------------------------------------------
def date2str(date_str):
  """Takes a string in YYYY-MM-DD form and returns a text string with the date in full English form.
  """
  if type(date_str) is not str:
    return 'Unknown'
  return datetime.fromisoformat(date_str).strftime('%B %e, %Y').replace('  ', ' ')


# INDEX PAGE: Top-level Menu
# =================================================================================================
# This is the entry point for the transfer application
@app.route('/', methods=['POST', 'GET'])
@app.route('/index/', methods=['POST', 'GET'])
def index_page():
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  # format_rules needs this for linking to review histories
  session['base_url'] = request.base_url

  """ Display menu of available features.
  """
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      cursor.execute("select count(*) from transfer_rules")
      num_rules = cursor.fetchone()[0]
      cursor.execute("select * from updates")
      updates = cursor.fetchall()
      rules_date = 'unknown'
      for update in updates:
        if update.table_name == 'transfer_rules':
          rules_date = date2str(update.update_date)

  # You can put messages for below the menu here:
  msg = f"""
  <footer id="update-info">
    <p><sup>&dagger;</sup>{num_rules:,} transfer rules as of {rules_date}.</p>
  </footer>
            """
  return render_template('top-menu.html',
                         title='Transfer Explorer',
                         result=Markup(top_menu(msg)),
                         omitjs=True)


# COURSE INFO PAGE
# =================================================================================================
@app.route('/course_info', methods=['GET'])
def course_info():
  """ Lots of information about a course.
  """
  try:
    title, result = _course_info(request.args['course'])
    return render_template('course_info.html', result=Markup(result), title=Markup(title))
  except KeyError:
    return render_template('404.html', result=Markup('<p class="error">No course specified</p>'), )


# REVIEW_RULES PAGE
# =================================================================================================
@app.route('/review_rules/', methods=['POST', 'GET'])
def review_rules():
  if app_unavailable():
    return render_template('app_unavailable.html', result=Markup(get_reason()))

  if DEBUG:
    print(f'{request.method} review_rules')

  # Dispatcher for forms
  dispatcher = {
      'do_form_1': do_form_1,
      'do_form_2': do_form_2,
      'do_form_3': do_form_3,
  }

  if request.method == 'POST':
    # User has submitted a form.
    return dispatcher.get(request.form['next-function'])(request, session)

  # Form not submitted yet, so call do_form_0 to generate form_1
  else:
    # clear institutions, subjects, and rules from the session before restarting
    session.pop('source_institutions', None)
    session.pop('destination_institutions', None)
    session.pop('source_disciplines', None)
    session.pop('destination_disciplines', None)
    return do_form_0(request, session)


# PENDING PAGE
# -------------------------------------------------------------------------------------------------
@app.route('/pending')
def pending():
  """ Display pending reviews.
      These are reviews that were submitted, but the user hasn’t responded to the confirmation
      email yet. They are automatically purged after 24 hours.
  """
  if app_unavailable():
    return render_template('app_unavailable.html', result=Markup(get_reason()))

  heading = header(title='Pending Reviews', nav_items=[{'type': 'link',
                                                        'href': '/',
                                                        'text': 'Main Menu'},
                                                       {'type': 'link',
                                                        'href': '/review_rules',
                                                        'text': 'Review Rules'}])
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      cursor.execute("""
        select email, reviews, to_char(when_entered, 'Month DD, YYYY HH12:MI am') as when_entered
          from pending_reviews""")

      if cursor.rowcount == 0:
        return render_template('review_rules.html', result=Markup(f"""
            {heading}
            <p class="instructions">There are no pending reviews.</p>
            """))

      result = f"""
                {heading}
                <p class="instructions">
                  The following reviews have been submitted within the past 48 hours, but the
                  submitter has not yet responded to an “activation” email message. Reviews not
                  activated within 48 hours of submission are ignored.
                </p>
                """
      for pending in cursor.fetchall():
        reviews = json.loads(pending.reviews)
        suffix = 's'
        if len(reviews) == 1:
          suffix = ''
        result += f"""
        <details>
          <summary>
            {len(reviews)} review{suffix} by {pending.email} on {pending.when_entered}
          </summary>
          <table>
            <tr><th>Rule</th><th>Type</th><th>Comment</th></tr>"""
        for review in reviews:
          result += f"""
                        <tr>
                          <td>{review['rule_key']}</td>
                          <td>{review['event_type']}</td>
                          <td>{review['comment_text']}</td>
                        </tr>"""
        result += '</table></details>'

  return render_template('review_rules.html', result=Markup(result), title='Pending Reviews')


# CONFIRMATION PAGE
# -------------------------------------------------------------------------------------------------
# This is the handler for clicks in the confirmation email.
# Notifications go to university_registrar, webmaster, and anyone identified with any sending or
# receiving college in the covered rules.
@app.route('/confirmation/<token>', methods=['GET'])
def confirmation(token):
  if app_unavailable():
    return render_template('app_unavailable.html', result=Markup(get_reason()))

  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      # Make sure the token is received and is in the pending table.
      heading = header(title='Review Confirmation', nav_items=[{'type': 'link',
                                                                'href': '/',
                                                                'text': 'Main Menu'},
                                                               {'type': 'link',
                                                                'href': '/review_rules',
                                                                'text': 'Review Rules'}])

      q = 'select * from pending_reviews where token = %s'
      cursor.execute(q, (token,))
      if cursor.rowcount == 0:
        msg = '<p class="error">This report has either expired or already been recorded.</p>'
      elif cursor.rowcount != 1:
        msg = f'<p class="error">Program Error: {cursor.rowcount} pending_reviews.</p>'
      else:
        msg, colleges = process_pending(cursor.fetchone())

        # Get list of people to notify
        q = """ select * from person_roles
                where role in ('cuny_registrar', 'webmaster')
                   or institution in ({})""".format(', '.join([f"'{c}'" for c in colleges]))
        cursor.execute(q)
        to_people = set()
        cc_people = set()
        bc_people = set()
        for person_role in cursor.fetchall():
          if person_role.role == 'cuny_registrar':
            cc_people.add(person_role)
          elif person_role.role == 'webmaster':
            bc_people.add(person_role)
          else:
            to_people.add(person_role)
        to_list = [{'email': p.email, 'name': p.name} for p in to_people]
        cc_list = [{'email': p.email, 'name': p.name} for p in cc_people]
        bcc_list = [{'email': p.email, 'name': p.name} for p in bc_people]
        try:
          from_person = bc_people.pop()
          from_addr = {'email': from_person.email, 'name': '  T-Rex Labs'}
        except KeyError:
          from_addr = {'email': 'cvickery@qc.cuny.edu', 'name': '  T-Rex Labs'}
        # Embed the html table in a complete web page
        html_body = """ <html><head><style>
                          table {border-collapse: collapse;}
                          td, th {
                            border: 1px solid blue;
                            padding:0.25em;
                          }
                        </style></head><body>
                    """ + msg.replace('/history', request.url_root + 'history') + '</body></html>'
        response = send_message(to_list,
                                from_addr,
                                subject='Transfer Rule Evaluation Received',
                                html_msg=html_body,
                                cc_list=cc_list,
                                bcc_list=bcc_list)
        if response.status_code != 202:
          msg += f'<p>Error sending notifications: {response.body}</p>'

  result = f"""
  {heading}
  <p><em>Review Report ID {token}</em></p>
  {msg}
  """
  return render_template('review_rules.html', result=Markup(result), title="Review Confirmation")


# HISTORY PAGE
# -------------------------------------------------------------------------------------------------
# Display the history of review events for a rule.
#
@app.route('/history/<rule>', methods=['GET'])
def history(rule):
  if app_unavailable():
    return render_template('app_unavailable.html', result=Markup(get_reason()))

  """ Look up all events for the rule, and report back to the visitor.
  """
  result = header(title='Event History', nav_items=[{'type': 'link',
                                                     'href': '/',
                                                     'text': 'Main Menu'},
                                                    {'type': 'link',
                                                     'href': '/review_rules',
                                                     'text': 'Review Rules'}])
  result += rule_history(rule)
  return render_template('review_rules.html',
                         result=Markup(result),
                         title='Review Event History')


# MAP_COURSES PAGE
# -------------------------------------------------------------------------------------------------
# Map courses at one instituition to all other other institutions, or vice-versa.
@app.route('/map_courses', methods=['GET'])
def map_courses():
  """ Prompt for a course (or set of courses in a discipline) at an institution, and display
      view-only information about rules that involve that or those courses.
      Display a CSV-downloadable table.
  """
  if app_unavailable():
    return render_template('app_unavailable.html', result=Markup(get_reason()))

  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      cursor.execute('select code, prompt from cuny_institutions order by prompt')

      options = [f"""
        <div class="institution-option">
          <input id="radio-{i.code}"
                 type="radio"
                 name="institution"
                 value="{i.code}" />
          <label for="radio-{i.code}">{i.prompt}</label>
        </div>
          """ for i in cursor.fetchall()]

  institution_select = '<div id="institutions">' + '\r'.join(options) + '</div>'
  # Supply colleges from db now, but use ajax to get a college's disciplines

  result = f"""
  <div id="setup-div">
    {header(title='Map Transfer Rules',
            nav_items=[{'type': 'link', 'href': '/', 'text': 'Main Menu'}])}
    <details class="instructions">
    <summary>Instructions</summary>
    <hr>
    <p>
      Select courses of interest in the “Which Courses” section. The number of courses selected
      will be shown.
    </p>
    <p>
      Then use the <span class="pseudo-button">Show Sending</span> button if you want to map
      how these courses transfer <em>to</em> courses at other institutions, or use the <span
      class="pseudo-button">Show Receiving</span> button if you want to map how these
      courses transfer <em>from</em> other institutions.
    </p>
    <p>
      If it takes too long to load the transfer map, reduce the number of courses selected. You
      can also limit the set of colleges mapped to senior, community, or comprehensives using the
      options in the “Which Colleges To Map” section.
    </p>
    </details>
    <form action="#" method="POST">
      <fieldset><h2>Which Courses</h2>
        <hr>
        <h2>
          Select one or more of the following groups of course levels.
        </h2>
        <div id="grouping-div">
          <label for="course-groups">Levels:</label>
          <select multiple id="course-groups" size="9">
            <option value="all">All course levels</option>
            <option value="below">Below 100-level courses</option>
            <option value="100">100-level courses</option>
            <option value="200">200-level courses</option>
            <option value="300">300-level courses</option>
            <option value="400">400-level courses</option>
            <option value="500">500-level courses</option>
            <option value="600">600-level courses</option>
            <option value="above">Above 600-level courses</option>
          </select>
          <p>
            <em>Note: Catalog numbers greater than 999 will be divided by ten until they are
            in the range 0 to 999 for grouping into levels.</em>
          </p>
        </div>
        <h2>
          Select a college and the discipline for the courses you are interested in.
        </h2>
        <div>
          <label for="institution">College:</label>
          {institution_select}
          <span id="discipline-span">
            <label for="discipline">Discipline:</label>
            <input type="text" id="discipline" />
          </span>
        </div>
        <p id="num-courses">
          No courses selected yet.
        </p>
      </fieldset>
      <fieldset><h2>Which Direction</h2>
        <hr>
        <p>
          Do you want to see how the selected courses transfer <em>to</em> other colleges
          (<em>sending rules</em>) or how they transfer <em>from</em> other colleges (<em>receiving
          rules</em>)?
        </p>
        <div class="center">
          <button id="show-sending">Sending Rules</button>
          |
          <button id="show-receiving">Receiving Rules</button>
          <span id="loading">Searching
            <span class="dot-1">.</span>
            <span class="dot-2">.</span>
            <span class="dot-3">.</span>
          </span>
        </div>
      </fieldset>
      <fieldset><h2>Which Colleges</h2>
        <hr>
        <input  type="checkbox"
                id="associates"
                name="which-colleges"
                value="associates"
                checked>
        <label for="associates" class="radio-label">Include Associates Degree Colleges</label>
        <input  type="checkbox"
                id="bachelors"
                name="which-colleges"
                value="bachelors"
                checked>
        <label for="bachelors" class="radio-label">Include Bachelor’s Degree Colleges</label>
      </fieldset>
    </form>
  </div>
  <div id="transfers-map-div">
    {header(title='Transfer Rule Map', nav_items=[{'type': 'link',
                                                   'href': '/',
                                                   'text': 'Main Menu'}, {'type': 'button',
                                                                          'id': 'show-setup',
                                                                          'text': 'Change Options'}
                                                  ])}
    <details class="instructions">
      <summary>
        The number of rules for transferring courses on the <span class="left-right">left</span>
        <span class="to-from">to</span> other colleges.
      </summary>
      <hr>
      <p>
        If the table below is empty, it means that all the courses selected are inactive and there
        are no rules for transferring them from any college. This is correct for inactive courses.
      </p>
      <p>
        If a cell contains zero, there are no rules for transferring the course
        <span class="to-from">to</span> that college. Values greater than one occur when there are
        multiple rules, for example when a course transfers as a particular destination course only
        if the student earned a minimum grade.
      </p>
      <p>
        If a course in the <span class="left-right">left</span>most column is <span
        class="inactive-course">highlighted like this</span>, it is inactive, and non-zero rule
        counts are <span class="bogus-rule">highlighted like this</span>. For sending courses, it is
        possible the rule would be used for students who completed the course before it became
        inactive. But for receiving courses, the rule is definitely an error.
      </p>
      <p>
        If a course is active but has zero values for some colleges, they are <span
        class="missing-rule">highlighted like this</span>.
      </p>
      <p>
        If a course transfers only as blanket credit, it is <span class="blanket-credit">highlighted
        like this</span>.
      </p>
      <p>
        If there are any rules that maps courses to their own institution, they are <span
        class="self-rule">highlighted like this</span>.
      </p>
      <p>
        Hover on courses on the <span class="left-right">left</span> to see their titles. Click on
        them to see complete catalog information.
      </p>
      <p>
        Click on non-zero cells to see details about those rules. (Hovering gives information for
        locating them in CUNYfirst.)
      </p>
    </details>
    <div class="table-height">
      <table id="transfers-map-table" class="scrollable">
      </table>
    </div>
  </div>
  <div id="pop-up-div">
    <div id="pop-up-container">
      <div id="dismiss-bar">x</div>
      <div id="pop-up-content"></div>
    </div>
  </div>
  """
  return render_template('map_courses.html', result=Markup(result), title='Map Course Transfers')


# /_INSTITUTIONS
# =================================================================================================
# AJAX access to the institutions table.
@app.route('/_institutions')
def _institutions():
  Institution = namedtuple('Institution', 'code, prompt, name, associates, bachelors')
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      cursor.execute("""select code, prompt, name, associates, bachelors
                          from cuny_institutions order by code
                     """)
      institutions = [Institution._make(x)._asdict() for x in cursor.fetchall()]

  return jsonify(institutions)


# /_DISCIPLINES
# =================================================================================================
# AJAX access to disciplines offered at a college
#
# Look up the disciplines and return the HTML for a select element named discipline.
@app.route('/_disciplines')
def _disciplines():
  institution = request.args.get('institution', 0)
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      cursor.execute("""select discipline
                          from cuny_disciplines
                          where cuny_subject != 'MESG'
                            and institution = %s
                          order by discipline""", (institution,))
      disciplines = ['<option value="{}">{}</option>'.format(x[0], x[0]) for x in cursor.fetchall()]

  return jsonify("""<select name="discipline" id="discipline">
    <option value="none" selected="selected">Select a Discipline</option>
    {}
    </select>""".format('\n'.join(disciplines)))


# /_FIND_COURSE_IDS
# ================================================================================================
# AJAX course_id lookup.
@app.route('/_find_course_ids')
def _find_course_ids():
  """ Given an institution and discipline, get all the matching course_ids. Then use range strings
      to select only the ones wanted (100-level, etc.)
      Return an array of {course_id, catalog_number} tuples.
      Cross-listing info (offer_nbr) is not included here because rules don’t know about them.
  """
  institution = request.args.get('institution')
  discipline = request.args.get('discipline')
  ranges_str = request.args.get('ranges_str')
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      cursor.execute("""select course_id, numeric_part(catalog_number) as cat_num
                        from cuny_courses
                        where institution = %s and discipline = %s
                     """, (institution, discipline))
      courses = [[c.course_id, c.cat_num] for c in cursor.fetchall()]

  # Filter out the deplorables
  # Range string syntax: all | min:max [;...]
  range_strings = ranges_str.split(';')
  ranges = []
  for range_string in range_strings:
    min, max = range_string.split(':')
    ranges.append((float(min), float((max))))

  # Keep courses whose numeric part is within one of the ranges
  keepers = []
  for course in courses:
    for range in ranges:
      if 'all' in ranges_str or course[1] >= range[0] and course[1] < range[1]:
        keepers.append(course)
        continue

  # The keepers list included the numeric part of catalog_number as a float so it could be sorted
  # before returning just the array of course_ids.
  keepers.sort(key=lambda c: c[1])
  return jsonify([c[0] for c in keepers])


# /_MAP_COURSE
# =================================================================================================
# AJAX generator of course_map table.
#
# Create a table row for each course_id in course_id_list; a column for each element in colleges.
# Table cells show how many rules there are for transferring that course to or from the institutions
# listed, with the title attribute of each cell being a colon-separated list of rule_keys (if any),
# and class attributes for bogus rules, etc.
# Request type tells which type of request: show-sending or show-receiving.
#
@app.route('/_map_course')
def _map_course():
  # Note to self: there has to be a cleaner way to pass an array from JavaScript
  course_ids = json.loads(request.args.getlist('course_list')[0])
  discipline = request.args.get('discipline')
  colleges = json.loads(request.args.getlist('colleges')[0])

  request_type = request.args.get('request_type', default='show-sending')

  table_rows = []
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      for course_id in course_ids:
        cursor.execute("""select  course_id,
                                  institution,
                                  discipline,
                                  catalog_number,
                                  title,
                                  course_status,
                                  designation
                          from cuny_courses
                          where course_id = %s
                          and discipline = %s
                       """, (course_id, discipline))
        if cursor.rowcount == 0:
          continue
        course_info = cursor.fetchone()
        class_info = 'selected-course'
        if course_info.course_status != 'A':
          class_info = 'selected-course inactive-course'
        course_info_cell = """
                             <th class="clickable {}"
                                 title="course_id {}: “{}”"
                                 headers="target-course-col"
                                 id="{}-row"
                                 >{} {} {}</th>
                           """.format(class_info,
                                      course_info.course_id,
                                      course_info.title,
                                      course_info.course_id,
                                      course_info.institution.rstrip('0123456789'),
                                      course_info.discipline,
                                      course_info.catalog_number)
        # Collect rules where the selected course is a sending course
        if request_type == 'show-sending':
          row_template = '<tr>' + course_info_cell + '{}</tr>'
          cursor.execute("""select distinct *
                            from transfer_rules r
                            where r.id in (select rule_id from source_courses where course_id = %s)
                            order by source_institution, subject_area, destination_institution
                        """, (course_info.course_id, ))

        else:
          # Collect rules where the selected course is a destination course
          row_template = '<tr>{}' + course_info_cell + '</tr>'
          cursor.execute("""select distinct *
                        from transfer_rules r
                        where r.id in (select rule_id from destination_courses where course_id = %s)
                        order by source_institution, subject_area, destination_institution
                        """, (course_info.course_id, ))
        all_rules = cursor.fetchall()

        # For each destination/source institution, need the count of number of rules and a list of
        # the rules.
        rule_counts = Counter()
        rules = defaultdict(list)
        for rule in all_rules:
          rule_key = '{}:{}:{}:{}'.format(rule.source_institution,
                                          rule.destination_institution,
                                          rule.subject_area,
                                          rule.group_number)
          if request_type == 'show-sending':
            rule_counts[rule.destination_institution] += 1
            rules[rule.destination_institution].append(rule_key)
          else:
            rule_counts[rule.source_institution] += 1
            rules[rule.source_institution].append(rule_key)

        # Ignore inactive courses for which there are no rules
        if sum(rule_counts.values()) == 0 and course_info.course_status != 'A':
          continue

        # Fill in the data cells for each college
        data_cells = ''
        for college in colleges:
          coll = college.strip('0123456789 ').lower()
          class_info = ''
          num_rules = rule_counts[college]
          if num_rules > 0:
            class_info = 'clickable '
          rules_str = '|'.join(rules[college])
          if (course_info.course_status == 'A'
             and num_rules == 0 and college != course_info.institution):
            class_info += 'missing-rule'
          if (num_rules == 1
             and (course_info.designation == 'MLA' or course_info.designation == 'MNL')):
            class_info += 'blanket-credit'
          if (course_info.course_status != 'A'
             and num_rules > 0 and college != course_info.institution):
            class_info += 'bogus-rule'
          if num_rules > 0 and college == course_info.institution:
            class_info += 'self-rule'
          class_info = class_info.strip()
          if class_info != '':
            class_info = f' class="{class_info}"'
          data_cells += f"""<td title="{rules_str}"
                                headers="{coll}-col {course_info.course_id}-row"
                                {class_info}>{num_rules}</td>"""
        table_rows.append(row_template.format(data_cells))

  return jsonify('\n'.join(table_rows))


# /_LOOKUP_RULES
# =================================================================================================
# AJAX access to the rules applicable to a course or set of courses.
#
# Returns up to two HTML strings, one for rules where the course(s) are a sending course, the other
# where it/they are a receiving course.
@app.route('/_lookup_rules')
def lookup_rules():
  institution = request.args.get('institution')
  discipline = request.args.get('discipline')
  original_catalog_number = request.args.get('catalog_number')
  # Munge the catalog_number so it makes a good regex and doesn't get tripped up by whitespace in
  # the CF catalog numbers.
  catalog_number = r'^\s*' + \
    original_catalog_number.strip(' ^').replace(r'\.', r'\\\.').replace(r'\\\\', r'\\')
  # Make sure it will compile when it gets to the db
  try:
    re.compile(catalog_number)
  except re.error:
    return jsonify("""
                   <p class="error">Invalid regular expression:
                   Unable to use "{}" as a catalog number.</p>""".format(original_catalog_number))
  type = request.args.get('type')
  # Get the course_ids
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      query = """
      select distinct course_id
        from cuny_courses
       where institution = %s
         and discipline = %s
         and catalog_number ~* %s
         and course_status = 'A'
         and discipline_status = 'A'
         and can_schedule = 'Y'
         and cuny_subject != 'MESG'
         """

      rules = ''
      cursor.execute(query, (institution, discipline, catalog_number))
      if cursor.rowcount > 0:
        course_ids = ', '.join(['{}'.format(x[0]) for x in cursor.fetchall()])

        # Get the rules
        if type == 'sending':
          source_dest = 'source'
        else:
          source_dest = 'destination'

        query = f"""select distinct
        source_institution||'-'||source_discipline||'-'||group_number||'-'||destination_institution
        from {source_dest}_courses
        where course_id in ({course_ids})
        order by
          source_institution||'-'||discipline||'-'||group_number||'-'||destination_institution
        """
        cursor.execute(query)
        rules = ['<div>{}</div>'.format(format_rule(x[0])) for x in cursor.fetchall()]
        credit_mismatch = False
        for rule in rules:
          if 'credit-mismatch' in rule:
            credit_mismatch = True
            break
        if credit_mismatch:
          rules.insert(0, """<p class="credit-mismatch">Rules higlighted like this have different
                       numbers of credits at the sending and receiving colleges.</p>""")
        rules.insert(0, '<p><em>Hover over catalog numbers for course details.</em></p>')
      if len(rules) == 0:
        if type == 'sending':
          rules = '<p>No sending rules</p>'
        else:
          rules = '<p>No receiving rules</p>'

  return jsonify(rules)


# /_RULES_TO_HTML
# =================================================================================================
# AJAX utility for converting a colon-separated list of rule keys into displayable description of
# the rules. Acts as an interface to format_rule().
@app.route('/_rules_to_html')
def _rules_to_html():
  rule_keys = request.args.get('rule_keys').split('|')
  return jsonify('<hr>'.join([format_rule_by_key(rule_key)[0] for rule_key in rule_keys]))


# /_COURSES
# =================================================================================================
# This route is for AJAX access to course catalog information.
#
# The request object has a course_ids field, which is a colon-separated list of course_ids.
# Look up each course, and return a list of html-displayable objects.
@app.route('/_courses')
def _courses():
  return_list = []
  course_ids = request.args.get('course_ids', 0)
  already_done = set()
  for course_id in course_ids.split(':'):
    if course_id in already_done:
      continue
    already_done.add(course_id)
    course, html = lookup_course(int(course_id), active_only=False)
    if course is not None:
      return_list.append({'course_id': course.course_id,
                          'institution': course.institution,
                          'department': course.department,
                          'discipline': course.discipline,
                          'catalog_number': course.catalog_number,
                          'title': course.title,
                          'html': html})
  return jsonify(return_list)


# /_COURSE_SEARCH
# =================================================================================================
#   AJAX search for a course, given the institution, discipline, and catalog number.
#   May return multiple matching courses, so return a list of html rather than just "the one".
@app.route('/_course_search')
def _course_search():
  search_str = request.args.get('search_string')
  return course_search(search_str)


# /_SESSIONS
# =================================================================================================
# This route is intended as a utility for pruning dead "session" entries from the db. A periodic
# script can access this url to prevent db bloat when millions of people start using the app. Until
# then, it's just here in case it's needed.
@app.route('/_sessions')
def _sessions():
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      q = 'select session_key, expiration_time from sessions order by expiration_time'
      cursor.execute(q)
      result = '<table>'
      now = datetime.now()
      num_expired = 0
      for row in cursor.fetchall():
        ts = datetime.fromtimestamp(row['expiration_time'])
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        status = 'active'
        if ts < now:
          status = 'expired'
          num_expired += 1
        result += '<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format(row['session_key'],
                                                                      ts_str,
                                                                      status)
      msg = '<p>There were no expired sessions to delete.</p>'
      if num_expired > 0:
        cursor.execute("delete from sessions where expiration_time < {}".format(now.timestamp()))
        conn.commit()
        cursor.close()
        conn.close()

        if num_expired == 1:
          msg = '<p>Deleted one expired session.</p>'
        else:
          msg = '<p>Deleted {} expired sessions.</p>'.format(num_expired)

  return result + '</table>' + msg


# COURSE REQUIREMENTS
# =================================================================================================
@app.route('/course_requirements/', methods=['POST', 'GET'])
def _course_requirements():
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  institution = request.args.get('institution', '')
  discipline = request.args.get('discipline', '')
  catalog_nbr = request.args.get('catalog_nbr', '')
  discipline_options = '<option value="">--Select a Discipline--</option>'

  if institution:
    if discipline:
      discipline_name = disciplines[institution][discipline]
      discipline_options = (f'<option value="{discipline}">{discipline_name}</option>\n'
                            f'{select_college_disciplines[institution]}</option>')
    else:
      discipline_options = ('<option value="">--Select a Discipline--</option>\n'
                            f'{select_college_disciplines[institution]}')

    college_options = (f'<option value="{institution}">{college_names[institution]}</option>\n'
                       f'{select_cuny_colleges}')
  else:
    college_options = '<option value="">--Select a College--</option>\n' + select_cuny_colleges
    discipline_options = '<option value="">--Select a College First--</option>'

  header_str = header(title='What Requirements Can Courses Satisfy',
                      nav_items=[{'type': 'link',
                                  'href': '/',
                                  'text': 'Main Menu'}])

  # Page starts with nav bar
  result = header_str

  # The form for selecting a course or courses. Always at top of page.
  result += f"""
  <section>
    <h2>Select Course(s)</h2>
    <form method="GET" action="/course_requirements">

      <label for="institution-select">College: </label>
      <select name="institution" id="institution-select">
        {college_options}
      </select>
      <br/>
      <label for="discipline-select">Discipline: </label>
      <select name="discipline" id="discipline-select">
        {discipline_options}
      </select>
      <br/>
      <label for="course-select">Catalog Number: </label>
      <input type="text" name="catalog_nbr" id="course-select" value="{catalog_nbr}"/>
      <div id="catalog-help">
        To select multiple courses within a discipline, you can use any of the following as
        the catalog number:
        <ul>
          <li>100-level, 200-level, 300-level, <em>or</em> 400-level</li>
          <li>1000-level, 2000-level, 3000-level, or 4000-level</li>
          <li>lower-division (<em>Catalog number starts with 0, 1, or 2</em>)</li>
          <li>upper-division (<em>Catalog number starts with 3, 4, 5, or 6</em>)</li>
          <li>any, all, <em>or</em> * (<em>All courses in the discipline</em>)

        </ul>

      </div>
      <br/>
      <button type="submit">Please</button>
    </form>
  </section>
  """

  # Info for course(s) selected
  if institution and discipline:
    try:
      if not catalog_nbr:
        raise ValueError('Enter Catalog Number')
      course_dicts = course_requirements.lookup_course(institution, discipline, catalog_nbr)
      if len(course_dicts) > 1:
        result += f'<h2>{len(course_dicts)} Matching Courses</h2>'
        for course_dict in course_dicts:
          result += f"""
  <details>
    <summary>
      {course_dict['discipline']} {course_dict['catalog_number']}:
      <em>{course_dict['course_title']}</em>
    </summary>
    {course_requirements.format_course(course_dict)}
  </details>
          """
      else:
        result += f"""
      <div class="course-info">
        {course_requirements.format_course(course_dicts[0])}
      </div>
      """
    except ValueError as err:
      result += f'<h2>{err}</h2>'

  return render_template('course_requirements.html', result=Markup(result))


# COURSES PAGE
# =================================================================================================
# Pick a college, and see catalog descriptions of all courses currently active there.
# Allow institution to come from the URL
@app.route('/courses/', methods=['POST', 'GET'])
def courses():
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      institution_code = None
      discipline_code = None
      department_code = None
      institution_name = 'Unknown'
      date_updated = 'Unknown'
      num_active_courses = 0
      discipline_clause = ''
      discipline_name = ''
      department_clause = ''
      department_str = ''
      if request.method == 'POST':
        institution_code = request.form['inst']
      else:
        institution_code = request.args.get('college', None)
        discipline_code = request.args.get('discipline', None)
        department_code = request.args.get('department', None)
        if institution_code is not None:
          institution_code = f'{institution_code[0:3].upper()}01'
          if discipline_code is not None:
            discipline_code = discipline_code.upper()
            discipline_clause = f"and discipline = '{discipline_code}'"
            cursor.execute(f"""select discipline_name
                                from cuny_disciplines
                               where institution = '{institution_code}'
                                 and discipline = '{discipline_code}'
                            """)
            if cursor.rowcount == 1:
              discipline_name = cursor.fetchone().discipline_name
          if department_code is not None:
            department_code = department_code.upper()
            department_clause = f"and department = '{department_code}'"
            cursor.execute(f"""select department_name
                                 from cuny_departments
                                where institution = '{institution_code}'
                                  and department = '{department_code}'
                            """)
            if cursor.rowcount == 1:
              department_str = f'Offered By the {cursor.fetchone().department_name} Department'

      if institution_code is not None:
        cursor.execute("select update_date from updates where table_name = 'cuny_courses'")
        date_updated = date2str(cursor.fetchone().update_date)
        cursor.execute('select name from cuny_institutions where code = %s', (institution_code, ))
        institution_name = cursor.fetchone().name
        cursor.execute(f"""
            select count(*) from cuny_courses
             where institution ~* %s {discipline_clause} {department_clause}
               and course_status = 'A'
               and can_schedule = 'Y'
               and discipline_status = 'A'
            """, (institution_code, ))
        num_active_courses = cursor.fetchone()[0]

        if discipline_name == '' and department_str == '':
          quantifier = 'All'
        else:
          quantifier = ''
        header_str = header(title=f'{institution_name}: {quantifier} Active Courses',
                            nav_items=[{'type': 'link',
                                        'href': '/',
                                        'text': 'Main Menu'},
                                       {'type': 'link',
                                        'href': '/courses',
                                        'text': 'Change College'}])
        result = f"""
          {header_str}
          <h1>{discipline_name} {department_str}</h1>
          <details class="instructions">
            <summary>Legend and Details</summary>
            <hr>
            <p>{num_active_courses:,} active courses as of {date_updated}</p>
            <p>Click on course name for transfer information.</p>
            <p>
              The following course properties are shown in parentheses at the bottom of each
              course’s catalog description. <em>Hover over items in this list for more information.
              </em>
            </p>
            <ul>
              <li title="CUNYfirst uses “career” to mean undergraduate, graduate, etc.">Career;</li>
              <li title="CUNY-standard name for the academic discipline">CUNY Subject;</li>
              <li id="show-attributes"
                  title="A course can have any number of attributes. Click here to see the names,
                  values, and descriptions for all attributes used at CUNY."> Course Attributes
                  (<em>None</em>, or a comma-separated list of name:value attribute pairs).
              </li>
            </ul>
            <div id="pop-up-div">
              <div id="pop-up-inner">
                <div id="dismiss-bar">x</div>
                <table>
                  <tr><th>Name</th><th>Value</th><th>Description</th></tr>
                  {course_attribute_rows}
                </table>
              </div>
            </div>
          </details>
          <p id="loading" class="error">Loading catalog information <span class="dot-1>.</span>
            <span class="dot-2">.</span class="dot-3"> <span>.</span>
          </p>
          """
        result += lookup_courses(institution_code,
                                 department=department_code,
                                 discipline=discipline_code)

      if num_active_courses == 0:
        # No courses yet (bogus or missing institution): prompt user to select an institution
        if (institution_code is not None
           or discipline_code is not None
           or department_code is not None):
          msg = '<p class="error">No Courses Found</p>'
        else:
          msg = ''
        result = f"""
        {header(title='  T-Rex Labs',
                nav_items=[{'type': 'link', 'text': 'Main Menu', 'href': '/'}])}
        <h1>List Active Courses</h1>{msg}
        <p class="instructions">Pick a college and say “Please”.</p>
        <form method="post" action="#">
        <fieldset><legend>Select a College</legend>"""
        cursor.execute("select * from cuny_institutions order by code")
        n = 0
        college_list = ''
        for row in cursor:
          n += 1
          college_list += """
          <div class='institution-select'>
            <input type="radio" name="inst" id="inst-{}" value="{}"/>
            <label for="inst-{}">{}</label>
          </div>
          """.format(n, row.code, n, row.name)

        result += f"""
          {college_list}
          <div>
            <button type="submit">Please</button>
          </div>
        </fieldset></form>
        <fieldset id="course-filters">
        <h2>Firehose Control</h2>
        <p>
          You can filter the courses at <span id="college-name">None</span> by department,
          discipline, CUNY subject, requirement designation, and/or course attribute.
        </p>
          <label for="department-select">Department:</label>
          <select id="department-select"name="department">
          </select>
          <br>
          <label for="discipline-select">Discipline:</label>
          <select id="discipline-select"name="discipline">
          </select>
          <br>
          <label for="subject-select">CUNY Subject:</label>
          <select id="subject-select"name="subject">
          </select>
          <br>
          <label for="designation-select">Designation:</label>
          <select id="designation-select"name="designation">
          </select>
          <br>
          <label for="attribute-select">Course Attribute:</label>
          <select id="attribute-select"name="attribute">
          </select>
        </fieldset>
        """
  return render_template('courses.html',
                         result=Markup(result),
                         title="Course Lists")


# REGISTERED PROGRAMS PAGE
# -------------------------------------------------------------------------------------------------
@app.route('/registered_programs/', methods=['GET'], defaults=({'institution': None}))
def registered_programs(institution, default=None):
  """ Show the academic programs registered with NYS Department of Education for any CUNY college.
  """
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  if institution is None:
    institution = request.args.get('institution', None)

  # Allow users to supply the institution in QNS01 or qns01 format; force to internal format ('qns')
  if institution is not None:
    institution = institution.lower().strip('01')
  else:
    institution = 'none'

  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      # For looking up individual plans in CUNYfirst

      # See when NYSED was last accessed
      try:
        cursor.execute("select update_date from updates where table_name='registered_programs'")
        nysed_update_date = (f'Latest NYSED website access was on '
                             f'{date2str(cursor.fetchone().update_date)}.')
      except (KeyError, ValueError):
        nysed_update_date = 'Date of latest NYSED website access is not available.'

      # See when Degree Works requirement_blocks were last updated.
      try:
        cursor.execute("select update_date from updates where table_name='requirement_blocks'")
        dgw_update_date = (f'Program requirements from Degree Works were last updated on  '
                           f'{date2str(cursor.fetchone().update_date)}.')
      except (KeyError, ValueError):
        dgw_update_date = 'Date of latest Degree Works access is not available.'

      # Find out what CUNY colleges are in the db
      cursor.execute("""
                     select distinct r.target_institution as inst, i.name
                     from registered_programs r, cuny_institutions i
                     where i.code = upper(r.target_institution||'01')
                     order by i.name
                     """)

      if cursor.rowcount < 1:
        result = """
        <h1>
          There is no registered-program information for CUNY colleges available at this time.
        </h1>
        """
        conn.close()
        return render_template('registered_programs.html', result=Markup(result))

      cuny_institutions = dict([(row.inst, {'name': row.name})
                               for row in cursor.fetchall()])
      cuny_institutions['all'] = {'name': 'All CUNY Colleges'}
      options = '\n'.join([f'<option value="{inst}">{cuny_institutions[inst]["name"]}</option>'
                          for inst in cuny_institutions])
      if institution is None or institution not in cuny_institutions.keys():
        h1 = '<h1>Select a CUNY College</h1>'
        html_table = ''
      else:
        # Complete the page heading with name of institution and link for downloading CSV
        csv_headings = ['Program Code',
                        'Registration Office',
                        'Institution',
                        'Program Title',
                        'Formats',
                        'HEGIS',
                        'Award',
                        'CIP Code',
                        'CUNY Program(s)',
                        'Certificate or License',
                        'Accreditation',
                        'First Reg. Date',
                        'Latest Reg. Action',
                        'TAP',
                        'APTS',
                        'VVTA']
        cursor.execute("select update_date from updates where table_name='registered_programs'")
        try:
          if cursor.rowcount != 1:
            raise RuntimeError('No CSV Available')
          else:
            filename = f'{institution.upper()}_{cursor.fetchone().update_date}.csv'
            if institution == 'all':
              cursor.execute("""
              select csv
                from registered_programs
            order by target_institution, title
            """)
            else:
              cursor.execute("""
              select csv
                   from registered_programs
                   where target_institution = %s
                   order by title
              """, (institution, ))
            if cursor.rowcount == 0:
              raise RuntimeError('No csv')

            # Try to (re-)create the csv file. If anything goes wrong, let me know.
            for row in cursor:
              csv_dir = Path(app.root_path + '/static/csv')
              csv_dir.mkdir(exist_ok=True)
              with open(f'{csv_dir}/{filename}', 'w') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(csv_headings)
                for row in cursor.fetchall():
                  line = json.loads(row.csv)
                  writer.writerow(line)
              link = (f' <a href="/static/csv/{filename}" download="{filename}"'
                      f'class="button">Download {filename}</a>')
        except (OSError, RuntimeError, json.JSONDecodeError):
          hostname = socket.gethostname()
          response = send_message(to_list=[{'email': 'Christopher.Vickery@qc.cuny.edu',
                                            'name': 'Christopher Vickery'}],
                                  from_addr={'email': 'Christopher.Vickery@qc.cuny.edu',
                                             'name': 'Christopher Vickery'},
                                  subject='Missing CSVs for registered programs',
                                  html_msg=f"""
                                  <p>You need to run <em>generate_html.py</em> on {hostname}</p>
                                  """)
          if response.status_code == 202:
            link = """
            <br>
            <span class="error">Information not available. I notified the webmaster.</span>
            """
          else:
            href_str = (f"mailto:Christopher.Vickery@qc.cuny.edu?"
                        f"subject='Transfer App: missing program information on {hostname}'")
            link = f"""
            <br>
            <span class="error">Information not available. Please report this to
              <a href="{href_str}"> Christopher Vickery</a>
            </span>'
            """

        # Generate the HTML table
        institution_name = cuny_institutions[institution]['name'] + link

        h1 = f'<h1>{institution_name}</h1>'

        nysed_url = 'http://www.nysed.gov/college-university-evaluation/format-definitions'
        html_headings = ['Program Code',
                         'Registration Office',
                         """Institution
                            <span class="sed-note">(Hover for NYSED Institution ID)</span>""",
                         'Program Title',
                         f'<a href="{nysed_url}"> Formats</a>',
                         'HEGIS',
                         'Award',
                         'CIP Code',
                         'CUNY Program(s)',
                         'Certificate or License',
                         'Accreditation',
                         'First Reg. Date',
                         'Latest Reg. Action',
                         '<span title="Tuition Assistance Program">TAP</span>',
                         '<span title="Aid for Part-Time Study">APTS</span>',
                         '<span title="Veteran’s Tuition Assistance">VVTA</span>']
        html_heading_row = '<thead><tr>' + ''.join([f'<th>{head}</th>' for head in html_headings])
        html_heading_row += '</tr></thead>\n'

        if institution == 'all':
          cursor.execute("""
          select html from registered_programs order by target_institution, title""")
        else:
          cursor.execute("""select html
                              from registered_programs
                              where target_institution = %s
                              order by title
                         """, (institution, ))
        html_data_rows = [f'{row.html}' for row in cursor.fetchall()]
        html_table_rows = html_heading_row + '<tbody>' + '\n'.join(html_data_rows) + '</tbody>'
        html_table = (f'<div class="table-height"><table class="scrollable">{html_table_rows}'
                      f'</table></div>')

      result = f"""
          {header(title='Registered Programs', nav_items=[{'type': 'link',
                                                           'text': 'Main Menu',
                                                           'href': '/'
                                                           }])}
          {h1}
            <form action="/registered_programs/" method="GET" id="select-institution">
              <select name="institution">
              <option value="none" style="font-size:3m; color:red;">Select a College</option>
              {options}
              </select>
          </form>
          <details>
            <summary>Instructions and Options</summary>
            <hr>
            <p>
              <span class="variant">Highlighted rows</span> are for programs with more than one
              variant, such as multiple institutions and/or multiple awards. For multiple
              institutions, the rows with matching Program Code numbers may not be next to each
              other because the table is ordered by Program Title, and the titles typically differ
              across institutions.
            </p>
            <p>
              The Registration Office is either the Department of Education’s Office of the
              Professions (OP) or its Office of College and University Evaluation (OCUE).
            </p>
            <p>
              Hover over HEGIS and CIP codes to see what they mean.<br>HEGIS is a NYS taxonomy of
              program areas. The values shown here come from the NYSED website. CIP is a Federal
              taxonomy, with the values shown here coming from CUNYfirst.
            </p>
            <p>
              The CUNY Programs column shows matching programs from CUNYfirst with the department
              that offers the program in parentheses. (Some programs are shared by multiple
              departments.) “Requirements” links in that column show the program’s requirements as
              given in Degree Works. {dgw_update_date}
            </p>
            <p>
              The rightmost three columns show financial aid eligibility. Hover over the headings
              for full names.
            </p>
            <p>
              {nysed_update_date}
            </p>
          </details>
          {html_table}
    """

  return render_template('registered_programs.html',
                         result=Markup(result),
                         title='Registered Programs')


# RULE CHANGES PAGE
# -------------------------------------------------------------------------------------------------
@app.route('/rule_changes/', methods=['GET'])
def rule_changes():
  first_date = request.args.get('first_date')
  second_date = request.args.get('second_date')
  if first_date == '' or first_date is None or second_date == '' or second_date is None:
    first_date, last_date = archive_dates()
    result = f"""
    {header(title='Rule Changes', nav_items=[{'type': 'link',
                                                     'text': 'Main Menu',
                                                     'href': '/'
                                                    }])}
    <h1>Select Dates</h1>
    <p>
      Select two dates to see what transfer rules have changed between them. Currently, there
      is a record of weekly changes between {first_date} and {last_date}.
    </p>
    <p>
      <em>It can take as long as two minutes to process your request, so please be patient!</em>
      <br>(If there is no response after two minutes, please let me know.)
    </p>
    <form action="/rule_changes">
      <label for="first_date">First Date:</label>
      <input type="date" name="first_date" id="first_date" value=""/> <span></span>
      <br>
      <label for="second_date">Second Date:</label>
      <input type="date" name="second_date" id="second_date" value=""/> <span></span>
      <br>
      <button type="select" id="submit_button">Look Up Changes</button> <span></span>
    </form>
    """
  else:
    first_date, second_date, diffs = diff_rules(first_date, second_date)
    first_date_str = date.fromisoformat(first_date).strftime('%B %-d, %Y')
    second_date_str = date.fromisoformat(second_date).strftime('%B %-d, %Y')
    result = f"""
    {header(title='Rule Changes', nav_items=[{'type': 'link',
                                                     'text': 'Main Menu',
                                                     'href': '/'
                                                    }])}
    <h1>Rule Changes</h1>
    <p>
      The following {len(diffs)} rules changed between {first_date_str} and {second_date_str}.
    </p>
    <table>
      <tr>
        <th>Type</th>
        <th>{first_date_str}</th>
        <th>{second_date_str}</th>
        <th>Rule Key<sup>1</sup></th></tr>
    """
    # Format table rows based on the diffs.
    table_rows = []
    with psycopg.connect('dbname=cuny_curriculum') as conn:
      with conn.cursor(row_factory=namedtuple_row) as cursor:
        for rule_key in sorted(diffs.keys()):
          rule_key_str = rule_key.replace('-', ':')
          delta_type, first_rule_text, second_rule_text = expand_delta(first_date,
                                                                       second_date,
                                                                       diffs[rule_key],
                                                                       cursor)
          table_rows.append(f"""
            <tr>
              <th>{delta_type}</th>
              <td>{first_rule_text}</td>
              <td>{second_rule_text}</td>
              <td>{rule_key_str}</td>
            </tr>""")

    nl = '\n'
    result += f"""
      {nl.join(table_rows)}
      </table>
      <hr>
      <sup>1</sup>The rule key contains information that could be used to locate the rule in
      CUNYfirst.
               """
  return render_template('rule_changes.html',
                         result=Markup(result),
                         title='Rule Changes')


def expand_delta(first_date, second_date, rules_dict, cursor):
  """ Determine the type of rule change, and fill in course information for the courses involved
  """
  delta_type = 'Change'
  if rules_dict[first_date] is None:
    first_rule_text = 'None'
    delta_type = 'Add'
  else:
    course_ids = ','.join(rules_dict[first_date][0])
    cursor.execute(f"""
         select institution, discipline, catalog_number, title, course_status
         from cuny_courses
         where course_id in ({course_ids})
         order by discipline, numeric_part(catalog_number)
         """)
    if cursor.rowcount > 0:
      first_rule_send = ','.join([f'<span title="{row.title}">{row.institution[0:3]}: '
                                  f'{row.discipline} {row.catalog_number}</span>'
                                  for row in cursor.fetchall()])
    else:
      first_rule_send = 'No sending courses'

    course_ids = ','.join(rules_dict[first_date][1])
    cursor.execute(f"""
         select institution, discipline, catalog_number, title, course_status
         from cuny_courses
         where course_id in ({course_ids})
         order by discipline, numeric_part(catalog_number)
         """)
    if cursor.rowcount > 0:
      first_rule_recv = ','.join([f'<span title="{row.title}">{row.institution[0:3]}: '
                                  f'{row.discipline} {row.catalog_number}</span>'
                                  for row in cursor.fetchall()])
    else:
      first_rule_recv = 'No receiving courses'

    first_rule_text = f'{first_rule_send} => {first_rule_recv}'

  if rules_dict[second_date] is None:
    second_rule_text = 'None'
    delta_type = 'Delete'
  else:
    course_ids = ','.join(rules_dict[second_date][0])
    cursor.execute(f"""
         select institution, discipline, catalog_number, title, course_status
         from cuny_courses
         where course_id in ({course_ids})
         order by discipline, numeric_part(catalog_number)
         """)
    if cursor.rowcount > 0:
      second_rule_send = ','.join([f'<span title="{row.title}">{row.institution[0:3]}: '
                                   f'{row.discipline} {row.catalog_number}</span>'
                                   for row in cursor.fetchall()])
    else:
      second_rule_send = 'No sending courses'

    course_ids = ','.join(rules_dict[second_date][1])
    cursor.execute(f"""
         select institution, discipline, catalog_number, title, course_status
         from cuny_courses
         where course_id in ({course_ids})
         order by discipline, numeric_part(catalog_number)
         """)
    if cursor.rowcount > 0:
      second_rule_recv = ','.join([f'<span title="{row.title}">{row.institution[0:3]}: '
                                   f'{row.discipline} {row.catalog_number}</span>'
                                   for row in cursor.fetchall()])
    else:
      second_rule_recv = 'No receiving courses'

    second_rule_text = f'{second_rule_send} => {second_rule_recv}'

  return delta_type, first_rule_text, second_rule_text


# _archive_dates()
# -------------------------------------------------------------------------------------------------
@app.route('/_archive_dates')
def _archive_dates():
  return json.dumps(available_archive_dates)


# /course_mappings route()
# -------------------------------------------------------------------------------------------------
# UNUSED ROUTE: CODE RETAINED AS HISTORICAL ARCHIVE
# @app.route('/course_mappings/', methods=['GET'])
# def course_mappings():
#   """ Display the program(s) for which a course satisfies requirement(s).
#       If the instutition, discipline, or catalog_num is not known, display a form to get them
#       first.
#   """
#   if app_unavailable():
#     return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

#   return render_template('course_mappings.html', result=Markup(course_mappings_impl(request)))


# download mapping tables
# -------------------------------------------------------------------------------------------------
@app.route('/download/<which>')
@app.route('/downloads/<which>')
def download_requests(which):
  """Download CSV files generated by the Requirements Mapper."""
  pattern = '.*(course|requirement|program|mapping).*'
  path_stem = 'static/csv/course_mapper.'
  try:
    request = re.match(pattern, which).group(1)
    match request:
      case 'course' | 'courses' | 'mapping' | 'mappings':
        return send_file(path_stem + 'course_mappings.csv',
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name='course_mappings.csv')
      case 'requirement' | 'requirements':
        return send_file(path_stem + 'requirements.csv',
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name='requirements.csv')
      case 'program' | 'programs':
        return send_file(path_stem + 'programs.csv',
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name='programs.csv')
      case _:
        raise AttributeError

  except (IndexError, AttributeError):
    return make_response('<h1>Unrecognized Download Request</h1>')


# PROGRAM DESCRIPTIONS PAGE
# -------------------------------------------------------------------------------------------------
@app.route('/describe_programs/')
def program_descriptions():
  """Prompt for a program, and display a description of some things known about the program.

  If the institution field includes a requirement_id, display that one automatically
  """
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  institution = request.args.get('institution')
  program_code = request.args.get('program-code')

  options = '<option value="">--select program--</option>'
  if institution is None:
    institution = ''
  try:
    institution, requirement_id_from_form = institution.split()
    requirement_id_from_form = f"RA{int(requirement_id_from_form.strip('RA')):06}"
  except ValueError:
    requirement_id_from_form = None
  institution = institution.upper().strip('01')

  if institution:
    options += options_dict[institution]['options_html']
    if program_code or requirement_id_from_form:
      code = program_code if program_code else requirement_id_from_form
      description = to_html(describe(institution[0:3], code))
    else:
      description = 'Please select a program.'
  else:
    description = 'Please select a college.'

  result = f"""
  {header(title='Describe Programs', nav_items=[{'type': 'link',
                                                  'text': 'Main Menu',
                                                  'href': '/'
                                                 },
                                                 {'type': 'link',
                                                  'text': 'Programs',
                                                  'href': '/registered_programs'
                                                 }])}
  <div class="instructions">
    <p>
      Select a college and a Major or Minor offered there to view a description of the program and
      any program-wide restrictions/requirements for it. All information is derived from the
      program’s Degree Works Scribe block(s).
    </p>
    <p>
      This is a development utility for cross-checking how programs are displayed by CUNY’s
      Transfer Explorer (T-Rex).
    </p>
    <p>
      You can add an RA# to the College box instead of selecting a Program, for example:
      <span class="code">qns 1343</span>
    </p>
    <h2 class="error">
    Updated: Majors, Minors, and Concentrations all work, and there’s a link from Major/Minors to
    their subprogram descriptions.<br>
    Selecting a Degree or Other block doesn’t work yet.
    </h2>
  </div>
  <fieldset><form id="lookup-program" method="GET" action="/describe_programs/">
  <label for="institution">College:</label> <input type="text"
                                                        name="institution"
                                                        value="{institution}"
                                                        id="institution"
                                                        placeholder="Which College?" />
  <br>
  <label for="program-code">Program: </label><select name="program-code"
                                                     id="program-code">
                                                     {options}
                                             </select>
  </form></fieldset>
  <div id="description">
    {description}
  </div>
  """

  return render_template('describe_programs.html',
                         result=Markup(result),
                         title='Describe Programs')


# WHAT REQUIREMENTS PAGE
# -------------------------------------------------------------------------------------------------
@app.route('/what_requirements/')
def what_requirements_does_this_course_satisfy():
  """
  """
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  course_query_str = request.args.get('course_query')
  if course_query_str is None:
    course_query_str = ''

  full_context = request.args.get('full_context') == 'on'
  full_context_checked = 'checked="checked"' if full_context else ''

  result = f"""
  {header(title='What Requirements?', nav_items=[{'type': 'link',
                                                  'text': 'Main Menu',
                                                  'href': '/'
                                                 },
                                                 {'type': 'link',
                                                  'text': 'Programs',
                                                  'href': '/registered_programs'
                                                 }])}
  <h1>What Requirements Does This Course Satisfy?</h1>
  <div class="instructions">
    <p>
      Enter a course_id or &lt;institution discipline catalog_number&gt; tuple to see what
      requirements the course satisfies at the college that offers it.
    </p>
  </div>
  <fieldset><form method="GET" action="/what_requirements/">
  <label for="full_context">Full Context</label> <input type="checkbox"
                                                        name="full_context"
                                                        {full_context_checked}
                                                        id="full_context" />
  <br>
  <label for="course_query_str">Course: </label><input type="text"
                                                      name="course_query"
                                                      id="course_query"
                                                      value="{course_query_str}"/>
  </form></fieldset>
  """
  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as course_cursor:
      if course_query := course_query_str.lower().split():
        valid_input = False
        match len(course_query):
          case 1:
            try:
              course_id = f'{int(course_query[0]):06}'
              course_cursor.execute("""
              select course_id, offer_nbr, institution, discipline, catalog_number,
                     designation, attributes
                from cuny_courses
               where course_id = %s
                 and course_status = 'A'
              """, (course_id, ))
              valid_input = True
            except ValueError:
              pass

          case 3:
            institution, discipline, catalog_number = course_query
            course_cursor.execute("""
            select course_id, offer_nbr, institution, discipline, catalog_number,
                   designation, attributes
              from cuny_courses
             where institution ~* %s
               and discipline ~* %s
               and catalog_number ~* %s
               and course_status = 'A'
            """, course_query)
            valid_input = True

          case _:
            pass

        if not valid_input:
          result += f'<h2>Invalid input: “{course_query_str}”</h2>'
        elif course_cursor.rowcount == 0:
          result += f'<h2>“{course_query_str}” not found</h2>'
        else:
          # Cross-listed courses will return multiple rows.
          for row in course_cursor:
            course_id = str(row.course_id)
            course_id_str = f'{row.course_id:06}:{row.offer_nbr}'
            if row.attributes != 'None':
              attributes = row.attributes.split(';')
              attributes = ', '.join([a.split(':')[1] for a in attributes])
            else:
              attributes = 'None'
            result += (f'<h2>{course_id_str} {row.institution[0:3]} {row.discipline:>6} '
                       f'{row.catalog_number:6} {row.designation:5} {attributes}</h2>')
            result += '<pre>' + ('\n'.join(what_requirements(course_id_str, full_context))) + '</pre>'

  return render_template('what_requirements.html',
                         result=Markup(result),
                         title='What Requirements?')


# REQUIREMENTS PAGE
# =================================================================================================

# /_requirement_values() -- AJAX support
# -------------------------------------------------------------------------------------------------
@app.route('/_requirement_values/')
def _requirement_values():
  """ Return a select element with the options filled in.
      # If the period is 'latest' include latest of all values.
      # Otherwise, include all values found.
      Generate options for all, and only, current blocks of the specified block_type. The option
      values are the requirement_id, but the option strings are block_type, title (requirement_id)
  """
  institution = request.args.get('institution', None)
  block_type = request.args.get('block-type', None)

  # Filter out all-numeric block_values; they are left over from "conversion"
  value_clause = r"and block_value !~ '^[\d ]+$' and block_value !~* '^mhc'"

  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      cursor.execute(f"""
      select requirement_id, block_value, title
        from requirement_blocks
       where institution = %s
         and period_stop ~* '^9'
         and block_type = %s
         {value_clause}
        order by block_value""", (institution, block_type))

      option_type = 'Concentration' if block_type == 'CONC' else block_type.title()

      options = ''
      if cursor.rowcount == 0:
        selected_option = (f'<option value="" selected="selected">No {block_type.title()} blocks '
                           f'found for {institution}</option>\n')
      else:
        selected_option = (f'<option value="" selected="selected">Select {option_type}</option>\n')
        for row in cursor.fetchall():
          requirement_id = f'({row.requirement_id})'

          options += (f'<option value="{row.requirement_id}">{row.block_value}: {row.title} '
                      f'{requirement_id}</option>\n')

  return f"""
    <label for="block-value" class="select" id="block-value-label">
      <strong>Requirement:</strong>
    </label>
    <select id="block-value">
    {selected_option}
    {options}
    </select>
      """


# /requirements route()
# -------------------------------------------------------------------------------------------------
@app.route('/requirements/', methods=['GET'])
def requirements(college=None, type=None, name=None, period=None):
  """ Display the requirements for a program.
      If the instutition, block_type, and block_value are not known, display a form to get them
      first.
  """
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  institution = request.args.get('institution')
  requirement_id = request.args.get('requirement_id')

  # If there is an institution and either a block_value or a requirement_num, JavaScript has
  # submitted the form.
  if institution is None or requirement_id is None:
    with psycopg.connect('dbname=cuny_curriculum') as conn:
      with conn.cursor(row_factory=namedtuple_row) as cursor:
        cursor.execute("select update_date from updates where table_name = 'requirement_blocks'")
        dgw_date = datetime.strptime(cursor.fetchone().update_date, '%Y-%m-%d')
        dgw_date = dgw_date.strftime('%B %d, %Y')

        cursor.execute('select code, prompt from cuny_institutions')
        college_choices = '<p><strong>Select a College:</strong></p>\n'
        for row in cursor.fetchall():
          college_choices += f"""<div class="institution-option">
                                   <input id="radio-{row.code}"
                                          type="radio"
                                          name="institution"
                                          value="{row.code}" />
                                   <label for="radio-{row.code}">{row.prompt}</label>
                                 </div>\n
                              """

    result = f"""
    {header(title='Requirements Search', nav_items=[{'type': 'link',
                                                      'text': 'Main Menu',
                                                      'href': '/'
                                                      },
                                                      {'type': 'link',
                                                       'text': 'Programs',
                                                       'href': '/registered_programs'
                                                      }])}
    <details class="disclaimer">
      <summary class="error">Research Project: Work in Progress</summary>
      <p class="error">
        The Scribe Blocks shown here, and their interpretations, are part of a research project to
        see if they can be used outside of the scope of the services already offered by the Ellucian
        Degree Works product.
      </p>
      <p>
        When Degree Works uses these Scribe Blocks, they have to be combined with a student’s
        academic record and other information maintained in the Degree Works system to produce
        reports such as degree audits, Transfer What-if analyses, and student program plans.
      </p>
      <p>
        This site presents “pure” program requirement information without connecting it to
        information about individual students.
      </p>
    </details>
    <details class="instructions">
      <summary>About This Project</summary>
      <p>
        This project is supported in part by grants from The Heckscher Foundation for Children and
        The Carroll and Milton Petrie Foundation to improve the transfer process at CUNY.
      </p>
      <p>
        This page lets you look up the current requirements for any degree, major, minor, or
        concentration at any CUNY college. The information is taken from the Degree Works “Scribe
        Blocks” that are designed to provide information based on individual students’ coursework
        completed and declared or prospective majors, minors, or concentrations.
      </p>
      <p>
        Once you select a degree or program on this page, the next page will show the code for the
        corresponding Scribe Block. We have parsed this code into a form that lets us discard the
        parts that only make sense in conjunction with individual a student’s academic record, and
        to present just the program requirements as they would apply to any student. This
        information becomes the basis for program-related featurs of CUNY’s Transfer Explorer
        website, <a href="https://explorer.cuny.edu">“T-Rex”</a>.
      <p>
      <p>
        Lists of courses in the Scribe language can use wildcards and ranges to make them more
        compact. We expand those lists to show all currently-active courses that match.
      </p>
      <p>
        Program requirements change over time. Here, we show only Scribe blocks for the current
        academic year. These blocks are subject to editorial changes from time to time, so the data
        are updated once a week to incorporate those changes.
      </p>
    </details>
      <fieldset>
        <form id="block-select-form" method="GET" action="/requirements">
          <input type="hidden" id="requirement-id" name="requirement_id" value='' />
          <div>
            {college_choices}
          </div>
          <div id="id-or-type-div">
            <hr>
            <p>
              If you know the ID number of the Scribe block you are interested in, enter it here.
            </p>
            <label for="requirement-num" class="select">RA-</label>
            <input type="number" id="requirement-num"
                   min="1"
                   max="999999"/>
             <hr>
            <div>
              <p>
                Alternatively, select a requirement type and specific requirement here.
              </p>
              <label for="block-type" class="select"><strong>Requirement Type:</strong></label>
              <select id="block-type">
              <option value="MAJOR">Major</option>
              <option value="MINOR">Minor</option>
              <option value="CONC">Concentration</option>
              <option value="OTHER">Other</option>
              <option value="DEGREE">Degree</option>
              </select>
            </div>

            <div id="block-value-div">
              <!-- Will come from AJAX -->
            </div>
          </div>
          <hr>
        </fieldset>
      </form>
      <p>
        <em>Degree Works information shown here was last updated on {dgw_date}.</em>
      </p>
      """
    return render_template('requirements_form.html',
                           result=Markup(result),
                           title='Select A Program')
  else:
    # Get the information about the block from the db
    with psycopg.connect('dbname=cuny_curriculum') as conn:
      with conn.cursor(row_factory=namedtuple_row) as cursor:
        cursor.execute(f"""
        select institution,
               requirement_id,
               block_type,
               block_value,
               title,
               period_start,
               period_stop,
               requirement_html,
               dgw_parse_tree
          from requirement_blocks
         where institution = '{institution}'
           and requirement_id = '{requirement_id}'
                            """)
        if cursor.rowcount < 1:
          return render_template('requirements_form.html',
                                 result=Markup(f'<h1 class="error">No Requirements Found</h1>'
                                               f'<p>{institution} {requirement_id}</p>'),
                                 title='No Requirements')
        requirements_html = '\n'.join([scribe_block_to_html(row)
                                      for row in cursor.fetchall()])

    result = f"""
    {header(title='Requirements Detail',
            nav_items=[{'type': 'link',
                        'text': 'Main Menu',
                        'href': '/'
                        },
                        {'type': 'link',
                         'text': 'Back',
                         'href': 'javascript:history.back()'
                        },

                        {'type': 'link',
                         'text': 'Search',
                         'href': '/requirements'
                        }])}
    {requirements_html}
    """
    return render_template('requirements.html', result=Markup(result))


@app.route('/_log_submits/', methods=['POST'])
def _log_submits():
  """Handle AJAX requests to log form submissions."""
  form_data = dict()
  for key, value in request.form.items():
    form_data[key] = value
  form_data['timestamp'] = str(datetime.now())[0:19]

  with psycopg.connect('dbname=cuny_curriculum') as conn:
    with conn.cursor(row_factory=namedtuple_row) as cursor:
      cursor.execute("""
      insert into submit_logs values (%s)
      """, (Json(form_data), ))

  return {'rowcount': cursor.rowcount}


@app.route('/_search_programs/', methods=['POST'])
def _search_programs():
  """Handle AJAX requests for search_programs.

  Given a text string and a list of colleges, return an object
  with the following keys:
    cip_codes: All the matching cip_codes found
    coarse: Matches by 2 cip digits
    medium: Matches by 4 cip digits
    fine: Matches by 6 cip digits
      plans: (institution, plan, enrollment) tuples
      subplans (institution, subplan, enrollent) tuples
  """
  if app_unavailable():
    return 'app_unavailable.html'

  search_request = request.get_json()
  search_result = find_programs(search_request)
  return search_result


@app.route('/search_programs/', methods=['GET'])
def search_programs():
  """Use cip_codes to find academic plans and subplans at CUNY.

  Generate the web page that will be updated dynamically by AJAX callbacks as the user interacts
  with the form
  """
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  # The web page includes input elements for search_text, colleges, plan, subplan options,
  # a count and list of matching cip_codes, and later on, the plans/subplans. There is no form to
  # submit: it's all AJAX
  result = f"""
      {header(title='Find Programs',
              nav_items=[{'type': 'link',
                          'text': 'Main Menu',
                          'href': '/'
                        }])}
  <h1>Search For Programs</h1>

  <h3>Use 2, 4, or 6 digit CIP codes to get lists of matching CUNY programs</h3>
  <p>
    What you type in the “What are you interested in?” box is compared to words in the titles of CIP
    codes and the CIP 2020 to SOC 2018 crosswalk.
  </p>
  <p>
    The “heuristic” slider tells what percentage of the words you type have to match the CIP/SOC
    words for a CIP code in order to include that CIP code. A heuristic value of zero ignores your
    words and shows all CUNY programs. 100% means that every word you type has to appear in the
    descriptions of the CIP and/or CIP-SOC titles.
  </p>
  <p>
    The numbers to the right of each program listed are the current enrollments in those programs.
  </p>
  <p>
    <label for="search-text">What are you interested in?</label>
      <input type="text" id="search_text"/>
    <br><label for="heuristic">Heuristic<span id="heuristic-value"></span>:</label>
      <input type="range" id="heuristic">

  </p>

  <fieldset><legend>2-digit</legend>
    <details>
      <summary><span id="num-coarse-cip">None yet</span></summary>
      <div id="coarse-cip-codes"></div>
    </details>
    <hr>
    <details>
      <summary><span id="num-coarse-plan">Zero</span> Academic Plans</summary>
      <div id="coarse-plans"></div>
    </details>
  </fieldset>

  <fieldset><legend>4-digit</legend>
    <details>
      <summary><span id="num-medium-cip">None yet</span></summary>
      <div id="medium-cip-codes"></div>
    </details>
    <hr>
    <details>
      <summary><span id="num-medium-plan">Zero</span> Academic Plans</summary>
      <div id="medium-plans"></div>
    </details>
  </fieldset>

  <fieldset><legend>6-digit</legend>
    <details>
      <summary><span id="num-fine-cip">None yet</span></summary>
      <div id="fine-cip-codes"></div>
    </details>
    <hr>
    <details>
      <summary><span id="num-fine-plan">Zero</span> Academic Plans</summary>
      <div id="fine-plans"></div>
    </details>
  </fieldset>
  """
  return render_template('search_programs.html', result=Markup(result))


@app.errorhandler(500)
def server_error(e):
  """Handle server errors."""
  return """
  An internal error occurred: <pre>{}</pre>
  See logs for full stacktrace.
  """.format(e), 500


@app.errorhandler(404)
def not_found_error(e):
  """Handle 404 errors."""
  result = f"""
  {header(title='CDIV', nav_items=[{'type': 'link',
                                           'text': 'Main Menu',
                                            'href': '/'
                                            }])}
  <h1 class="error">Not Found!</h1>
  <ul>
    <li>
      The app is being updated often. so you may need to refresh your browser to get the current
      versions of internal links.
    </li>
    <li>
      If you are coming from a saved URL, you may need to go back to the Main Menu to access
      current links.
    </li>
    <li>
      If this is a broken link in the app (or any other problem with it), please let me know.<br>
      <em><a href="mailto:cvickery@qc.cuny.edu?subject='Transfer App issue'">Christopher
      Vickery</a></em>.
    </li>
  </ul>
  """
  return render_template('404.html', result=Markup(result), )


if __name__ == '__main__':
  # This is used when running locally. Gunicorn is used to run the application online.
  # 2021-11-05: changed port from 5000 to 5001 to deal with MacOS 12's use of 5000.
  # 2021-11-06: reverted to 5000. Decided to turn off AirPlay receiver instead.

  PORT = 5000 if os.getenv('TREX_PORT') is None else int(os.getenv('TREX_PORT'))
  app.run(host='0.0.0.0', port=PORT, debug=True)
