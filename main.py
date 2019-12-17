#! /usr/local/bin/python3
# CUNY Transfer Explorer
# C. Vickery

import sys
import os
import re
import socket

import json
from datetime import datetime, timedelta

from collections import namedtuple
from collections import defaultdict
from collections import Counter

import psycopg2
from psycopg2.extras import NamedTupleCursor

from course_lookup import lookup_courses, lookup_course
from sendemail import send_token, send_message
from reviews import process_pending
from rule_history import rule_history
from format_rules import format_rule, format_rules, format_rule_by_key, \
    Transfer_Rule, Source_Course, Destination_Course, andor_list
from course_lookup import course_attribute_rows, course_search

from known_institutions import known_institutions

from system_status import app_available, app_unavailable, get_reason, \
    start_update_db, end_update_db, start_maintenance, end_maintenance

from app_header import header
from top_menu import top_menu

from review_rules import do_form_0, do_form_1, do_form_2, do_form_3
from propose_rules import _propose_rules

from requirements import get_requirements_text
from dgw_parser import dgw_parser

from flask import Flask, url_for, render_template, make_response,\
    redirect, send_file, Markup, request, jsonify, session
from flask_session import Session

SESSION_TYPE = 'redis'
PERMANENT_SESSION_LIFETIME = timedelta(days=90)
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config.from_object(__name__)
Session(app)

# During local development, enable more detailed log messages from the app.
if os.getenv('DEVELOPMENT') is not None:
  DEBUG = True
else:
  DEBUG = False


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
  return datetime.fromisoformat(date_str).strftime('%B %e, %Y').replace('  ', ' ')


# fix_title()
# -------------------------------------------------------------------------------------------------
def fix_title(str):
  """ Create a better titlecase string, taking specifics of the registered_programs dataset into
      account.
  """
  return (str.strip(' *')
             .title()
             .replace('Cuny', 'CUNY')
             .replace('Mhc', 'MHC')
             .replace('Suny', 'SUNY')
             .replace('\'S', '’s')
             .replace('1St', '1st')
             .replace('6Th', '6th')
             .replace(' And ', ' and ')
             .replace(' Of ', ' of '))


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
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute("select count(*) from transfer_rules")
  num_rules = cursor.fetchone()[0]
  cursor.execute("select * from updates")
  updates = cursor.fetchall()
  catalog_date = 'unknown'
  rules_date = 'unknown'
  for update in updates:
    if update.table_name == 'courses':
      catalog_date = date2str(update.update_date)
    if update.table_name == 'transfer_rules':
      rules_date = date2str(update.update_date)
  cursor.close()
  conn.close()
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


# REVIEW RULES PAGES
# -------------------------------------------------------------------------------------------------
#   Not posted: display form_1, which displays email prompt, source, and destination lists. User
#   must provide email and select exactly one institution from one of the lists and 1+ institutions
#   from the other list.
#   Posted form_1: display form_2, which provides list of disciplines for the single institution.
#   The user may select 1+ of them.
#   Posted form_2: display form_3, which provides matching transfer rules for all discipline pairs
#   selected. For each one, display a "verified" checkbox and a "notation" text box.
#   Posted form_3: enter all verified/notation data, along with person's email into db; send email
#   for confirmation. When user replies to the email, mark all matching items as confirmed and
#   notify the proper authorities. If confirmation email says no, notify OUR, who can delete them.
#   (This allows people to accidentally deny their work without losing it.)

@app.route('/propose_rules', methods=['POST', 'GET'])
def propose_rules():
  return render_template('propose_rules.html', result=Markup(_propose_rules()))


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
    return dispatcher.get(request.form['next-function'], lambda: error)(request, session)

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
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
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
              The following reviews have been submitted within the past 48 hours, but the submitter
              has not yet responded to an “activation” email message. Reviews not activated within
              48 hours of submission are ignored.
            </p>
            """
  for pending in cursor.fetchall():
    reviews = json.loads(pending.reviews)
    suffix = 's'
    if len(reviews) == 1:
      suffix = ''
    result += f"""
    <details>
      <summary>{len(reviews)} review{suffix} by {pending.email} on {pending.when_entered}</summary>
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
  cursor.close()
  conn.close()

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

  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)

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
     from_addr = {'email': from_person.email, 'name': 'CUNY Transfer App'}
    except KeyError:
      from_addr = {'email': 'cvickery@qc.cuny.edu', 'name': 'CUNY Transfer App'}
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
  cursor.close()
  conn.close()

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

  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute('select code, prompt from institutions order by prompt')
  options = ['<option value="{}">{}</option>'.format(x[0], x[1]) for x in cursor.fetchall()]
  conn.close()
  institution_select = """
  <select id="institution" name="institution">
    <option value="none" selected="selected">Select a College</option>
    {}
  </select>
  """.format('\n'.join(options))
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
    {header(title='Transfer Rule Map',
            nav_items=[{'type': 'link', 'href': '/', 'text': 'Main Menu'},
                       {'type': 'button',
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
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute("""select code, prompt, name, associates, bachelors
                      from institutions order by code
                 """)
  institutions = [Institution._make(x)._asdict() for x in cursor.fetchall()]

  conn.close()
  return jsonify(institutions)


# /_DISCIPLINES
# =================================================================================================
# AJAX access to disciplines offered at a college
#
# Look up the disciplines and return the HTML for a select element named discipline.
@app.route('/_disciplines')
def _disciplines():
  institution = request.args.get('institution', 0)
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute("""select discipline
                      from cuny_disciplines
                      where cuny_subject != 'MESG'
                        and institution = %s
                      order by discipline""", (institution,))
  disciplines = ['<option value="{}">{}</option>'.format(x[0], x[0]) for x in cursor.fetchall()]
  conn.close()
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
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute("""select course_id, numeric_part(catalog_number) as cat_num
                    from courses
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
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  for course_id in course_ids:
    cursor.execute("""select  course_id,
                              institution,
                              discipline,
                              catalog_number,
                              title,
                              course_status,
                              designation
                      from courses
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

    # For each destination/source institution, need the count of number of rules and a list of the
    # rules.
    rule_counts = Counter()
    rules = defaultdict(list)
    for rule in all_rules:
      rule_key = '{}-{}-{}-{}'.format(rule.source_institution,
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
      rules_str = ':'.join(rules[college])
      if course_info.course_status == 'A' and num_rules == 0 and college != course_info.institution:
        class_info += 'missing-rule'
      if num_rules == 1 and (course_info.designation == 'MLA' or course_info.designation == 'MNL'):
        class_info += 'blanket-credit'
      if course_info.course_status != 'A' and num_rules > 0 and college != course_info.institution:
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

  conn.close()
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
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  query = """
  select distinct course_id
    from courses
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

    query = """
    select distinct
        source_institution||'-'||source_discipline||'-'||group_number||'-'||destination_institution
      from {}_courses
     where course_id in ({})
     order by source_institution||'-'||discipline||'-'||group_number||'-'||destination_institution
    """.format(source_dest, course_ids)
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
  rule_keys = request.args.get('rule_keys').split(':')
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
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
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


# COURSES PAGE
# =================================================================================================
# Pick a college, and see catalog descriptions of all courses currently active there.
# Allow institution to come from the URL
@app.route('/courses/', methods=['POST', 'GET'])
def courses():
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
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
      if not re.search(r'\d\d$', institution_code):
        institution_code += '01'
      institution_code = institution_code.upper()
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
    cursor.execute("""
              select name, date_updated
                from institutions
               where code ~* %s
               """, (institution_code,))
    if cursor.rowcount == 1:
      # Found a college: find out if it offers some courses
      row = cursor.fetchone()
      institution_name = row.name
      date_updated = row.date_updated.strftime('%B %e, %Y')
      cursor.execute(f"""
          select count(*) from courses
           where institution ~* %s {discipline_clause} {department_clause}
             and course_status = 'A'
             and can_schedule = 'Y'
             and discipline_status = 'A'
          """, (institution_code,))
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
        <p>
          The following course properties are shown in parentheses at the bottom of each course’s
          catalog description. <em>Hover over items in this list for more information. </em> </p>
        <ul>
          <li title="CUNYfirst uses “career” to mean undergraduate, graduate, etc.">Career;</li>
          <li title="CUNY-standard name for the academic discipline">CUNY Subject;</li>
          <li title="Each course has exactly one Requirement Designation (RD). Among other values,
          Pathways requirements appear here.">
            Requirement Designation;</li>
          <li id="show-attributes"
              title="A course can have any number of attributes. Click here to see the names,
              values, and descriptions for all attributes used at CUNY.">
              Course Attributes (<em>None</em>, or a comma-separated list of name:value attribute
              pairs).
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
    result = result + lookup_courses(institution_code,
                                     department=department_code,
                                     discipline=discipline_code)

  if num_active_courses == 0:
    # No courses yet (bogus or missing institution): prompt user to select an institution
    if (institution_code is not None or discipline_code is not None or department_code is not None):
      msg = '<p class="error">No Courses Found</p>'
    else:
      msg = ''
    result = f"""
    {header(title='CUNY Transfer App',
            nav_items=[{'type':'link', 'text': 'Main Menu', 'href': '/'}])}
    <h1>List Active Courses</h1>{msg}
    <p class="instructions">Pick a college and say “Please”.</p>
    <form method="post" action="#">
    <fieldset><legend>Select a College</legend>"""
    cursor.execute("select * from institutions order by code")
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
    cursor.close()
    conn.close()
    result += f"""
      {college_list}
      <div>
        <button type="submit">Please</button>
      </div>
    </fieldset></form>
    <fieldset id="course-filters">
    <h2>Firehose Control</h2>
    <p>
      You can filter the courses at <span id="college-name">None</span> by department, discipline,
      CUNY subject, requirement designation, and/or course attribute.
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


# REGISTERED PROGRAMS PAGES
# =================================================================================================
#
@app.route('/download_csv/<filename>')
def download_csv(filename):
  """ Download csv file with the registered programs information for a college.
      THIS IS FRAGILE: The project directory for scraping the NYS DOE website must be located in
      the same folder as this app’s project directory, and it must be named registered_programs.
  """
  return send_file(os.path.join(app.root_path,
                                f'../registered_programs/csv_files/{filename}'))


@app.route('/registered_programs/', methods=['GET'], defaults=({'institution': None}))
def registered_programs(institution, default=None):
  """ Show the academic programs registered with NYS Department of Education for any CUNY college.
  """
  if institution is None:
    institution = request.args.get('institution', None)

  # Allow users to supply the institution in QNS01 or qns01 format; force to internal format ('qns')
  if institution is not None:
    institution = institution.lower().strip('01')
  else:
    institution = 'none'

  # See when the db was last updated
  conn = psycopg2.connect('dbname=cuny_courses')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  plan_cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  dgw_conn = psycopg2.connect('dbname=cuny_programs')
  dgw_cursor = dgw_conn.cursor(cursor_factory=NamedTupleCursor)
  try:
    cursor.execute("select update_date from updates where table_name='registered_programs'")
    update_date = date2str(cursor.fetchone().update_date)
  except (KeyError, ValueError):
    update_date = '(<em>None or in progress</em>)'
  try:
    dgw_cursor.execute("select last_update from updates where institution = %s",
                       (institution.upper() + '01', ))
    dgw_update_date = (f'for this college was last updated on ' +
                       date2str(str(dgw_cursor.fetchone().last_update)) + '.')
  except (KeyError, ValueError, AttributeError) as e:
    if institution == 'none':
      dgw_update_date = 'is not available until you select a college.'
    elif institution == 'all':
      dgw_update_date = 'is not available when “All CUNY Colleges” is selected.'
    else:
      dgw_update_date = 'is not available.'

  # Find out what CUNY colleges are in the db
  cursor.execute("""
                 select distinct r.target_institution as inst, i.name
                 from registered_programs r, institutions i
                 where i.code = upper(r.target_institution||'01')
                 order by i.name
                 """)

  if cursor.rowcount < 1:
    result = """
    <h1>There is no registered-program information for CUNY colleges available at this time.</h1>
    """
    return render_template('registered_programs.html', result=Markup(result))

  cuny_institutions = dict([(row.inst, row.name) for row in cursor.fetchall()])
  cuny_institutions['all'] = 'All CUNY Colleges'
  options = '\n'.join([f'<option value="{inst}">{cuny_institutions[inst]}</option>'
                      for inst in cuny_institutions])
  csv_link = ''
  if institution is None or institution not in cuny_institutions.keys():
    h1 = '<h1>Select a CUNY College</h1>'
    table = ''
  else:
    # Complete the page heading
    institution_name = cuny_institutions[institution]

    # List of short CUNY institution names plus known non-CUNY names
    # Start with the list of all known institutions, then replace CUNY names with their short names.
    short_names = dict()
    for key in known_institutions.keys():
      short_names[key] = known_institutions[key][1]  # value is (prog_code, name, is_cuny)
    cursor.execute("""
                      select code, prompt
                        from institutions
                   """)
    for row in cursor.fetchall():
      short_names[row.code.lower()[0:3]] = row.prompt
    # Link to the current csv file, if there is one.
    csv_dir = '../registered_programs/csv_files'
    all_clause = ' (<em>Does not include the “CUNY Program(s)” column.</em>)'
    for filename in os.listdir(csv_dir):
      if filename.startswith(institution.upper()):
        if institution == 'all':
          all_clause = ''
        csv_link = f"""<a download class="button" href="/download_csv/{filename}">
                       Download {filename}</a>{all_clause}<br/>"""
        break
    h1 = f'<h1>{institution_name}</h1>'

    # Generate the HTML table: headings
    headings = ['Program Code',
                'Registration Office',
                'Institution',
                'Title',
                """<a href="http://www.nysed.gov/college-university-evaluation/format-definitions">
                   Formats</a>""",
                'HEGIS',
                'Award',
                'CUNY Program(s)',
                'Certificate or License',
                'Accreditation',
                'First Reg. Date',
                'Latest Reg. Action',
                '<span title="Tuition Assistance Program">TAP</span>',
                '<span title="Aid for Part-Time Study">APTS</span>',
                '<span title="Veteran’s Tuition Assistance">VVTA</span>']
    heading_row = '<thead><tr>' + ''.join([f'<th>{head}</th>' for head in headings])
    heading_row += '</tr></thead>\n'

    # Generate the HTML table: data rows
    if institution == 'all':
      institution = ''  # regex will match all values
    cursor.execute("""
                   select program_code,
                          unit_code,
                          institution,
                          title,
                          formats,
                          hegis,
                          award,
                          certificate_license,
                          accreditation,
                          first_registration_date,
                          last_registration_action,
                          tap, apts, vvta,
                          is_variant
                   from registered_programs
                   where target_institution ~ %s
                   order by title, program_code
                   """, (institution,))
    data_rows = []
    for row in cursor.fetchall():
      if row.is_variant:
        class_str = ' class="variant"'
      else:
        class_str = ''

      values = list(row)
      values.pop()  # Don’t display is_variant value: it is indicated by the row’s class.

      # If the institution column is a numeric string, it’s a non-CUNY partner school, but the
      # name is available in the known_institutions dict.
      if values[2].isdecimal():
        values[2] = fix_title(known_institutions[values[2]][1])

      # Insert list of all CUNY programs (plans) for this program code
      plan_cursor.execute("""
                            select * from cuny_programs
                             where nys_program_code = %s
                             and program_status = 'A'""", (values[0],))
      cell_content = ''
      if plan_cursor.rowcount > 0:
        plans = plan_cursor.fetchall()
        # There is just one program and description per college, but the program may be shared
        # among multiple departments at a college.
        Program_Info = namedtuple('Program_Info', 'program program_title departments')
        program_info = dict()
        program_departments = []
        program = None
        program_title = None
        for plan in plans:
          institution_key = plan.institution.lower()[0:3]
          if institution_key not in program_info.keys():
            program_info[institution_key] = Program_Info._make([plan.academic_plan,
                                                               plan.description,
                                                               []
                                                                ])
          program_info[institution_key].departments.append(plan.department)

        # Add information for this institution to the table cell
        if len(program_info.keys()) > 1:
          cell_content += '— <em>Multiple Institutions</em> —<br>'
          show_institution = True
        else:
          show_institution = False
        for inst in program_info.keys():
          program = program_info[inst].program
          program_title = program_info[inst].program_title
          if show_institution:
            if inst in short_names.keys():
              inst_str = f'{short_names[inst]}: '
            else:
              inst_str = f'{inst}: '
          else:
            inst_str = ''
          departments_str = andor_list(program_info[inst].departments)
          cell_content += f" {inst_str}{program} ({departments_str})<br>{program_title}"
          # If there is a dgw requirement block for the plan, use link to it
          dgw_cursor.execute("""
                             select *
                               from requirement_blocks
                              where institution ~* %s
                                and block_value = %s
                             """, (institution, plan.academic_plan))
          if dgw_cursor.rowcount > 0:
            cell_content += (f'<br><a href="/requirements/?'
                             f'college={institution.upper() + "01"}&type=MAJOR&name={program}">'
                             'Requirements</a>')
          if show_institution:
            cell_content += '<br>'

      values.insert(7, cell_content)
      cells = ''.join([f'<td>{value}</td>' for value in values])
      data_rows.append(f'<tr{class_str}>{cells}</tr>')
    table_rows = heading_row + '<tbody>' + '\n'.join(data_rows) + '</tbody>'
    table = f'<div class="table-height"><table class="scrollable">{table_rows}</table></div>'
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
          <span class="variant">Highlighted rows</span> are for programs with more than one variant,
          such as multiple institutions and/or multiple awards.
        </p>
        <p>
          The Registration Office is either the Department of Education’s Office of the Professions
          (OP) or its Office of College and University Evaluation (OCUE).
        </p>
        <p>
          The CUNY Programs column shows matching programs from CUNYfirst with the department that
          offers the program in parentheses. (Some programs are shared by multiple departments.)
          “Requirements” links in that column show the program’s requirements as given in
          Degreeworks. Degreeworks information {dgw_update_date}
        </p>
        <p>
          The last three columns show financial aid eligibility. Hover over the headings for
          full names.
        </p>
        <p>
          Latest NYS Department of Education access was on {update_date}.
        </p>
        <p>
          {csv_link}
        </p>
      </details>
      {table}
"""
  conn.close()
  return render_template('registered_programs.html',
                         result=Markup(result),
                         title='Registered Programs')


@app.route('/_requirement_values/')
def _requirement_values():
  """ Return a select element with the options filled in.
      If the period is 'current' include only values where the period is '999999'.
      Otherwise, include all values found.

  """
  institution = request.args.get('institution', 0)
  block_type = request.args.get('block_type', 0)
  period = request.args.get('period', 0)
  period_clause = ''
  if period == 'current':
    period_clause = "and period_stop = '99999999'"
  # DEVELOPMENT PARAMETER
  # Durning development, filter out all-numeric values
  value_clause = r"and block_value !~ '^[\d ]+$'"
  option_type = f'a {block_type.title()}'
  if block_type == 'CONC':
    option_type = 'a Concentration'
  if block_type == 'OTHER':
    option_type = 'a Requirement'
  conn = psycopg2.connect('dbname=cuny_programs')
  cursor = conn.cursor(cursor_factory=NamedTupleCursor)
  cursor.execute(f"""select distinct block_value, title
                       from requirement_blocks
                      where institution = %s
                        and block_type = %s
                       {period_clause}
                       {value_clause}
                      order by block_value""", (institution, block_type))
  print(cursor.query)
  options = '\n'.join([f'<option value="{r.block_value}">{r.block_value}: {r.title}</option>\n'
                      for r in cursor.fetchall()])
  conn.close()
  return f"""<option value="" selected="selected">Select {option_type}</option>\n
                 {options}"""


@app.route('/requirements/', methods=['GET'])
def requirements(college=None, type=None, name=None, period=None):
  """ Display the requirements for a program.
      If the instutition, block_type, and block_value are not known, display a form to get them
      first.
  """
  institution = request.args.get('college')
  b_type = request.args.get('type')
  b_value = request.args.get('name')
  period = request.args.get('period')
  if period is None:
    period = 'current'
  if institution is None or b_type is None or b_value is None:
    conn = psycopg2.connect('dbname=cuny_programs')
    cursor = conn.cursor(cursor_factory=NamedTupleCursor)
    cursor.execute("select distinct last_update from updates where institution != 'HEGIS'")
    dgw_date = cursor.fetchone().last_update
    dgw_date = dgw_date.strftime('%B %d, %Y')
    conn.close()
    conn = psycopg2.connect('dbname=cuny_courses')
    cursor = conn.cursor(cursor_factory=NamedTupleCursor)
    cursor.execute('select code, name from institutions')
    college_options = '<option value="">Select College</option>\n'
    for row in cursor.fetchall():
      college_options += f'<option value="{row.code}">{row.name}</option>\n'
    result = f"""
    {header(title='Requirements Request', nav_items=[{'type': 'link',
                                              'text': 'Main Menu',
                                              'href': '/'
                                              }])}
    <h1 class="error">Proof of Concept</h1>
    <details><summary>More Information</summary>
    <p>
      This form lets you examine the information from any CUNY  Degreeworks “Scribe Block.”
      The information returned is incomplete at this time, but what is shown is extracted from
      the actual Degreewoks information used to determine program and degree requirements for
      graduation.
    </p>
    <p>
      Degreeworks information last updated on {dgw_date}.
    </p>
    </details>
    <fieldset><legend>Select Requirements</legend>
    <form method="GET" action="/requirements">
      <div>
        <label for="institution">College:</label>
        <select id="institution" name="college" placeholder="Select College">
          {college_options}
        </select>
      </div>

      <div>
        <label for="block-type">Requirement Type:</label>
        <select id="block-type" name="type">
        <option value="DEGREE">Degree</option>
        <option value="MAJOR">Major</option>
        <option value="MINOR">Minor</option>
        <option value="CONC">Concentration</option>
        <option value="OTHER">Other</option>
        </select>
      </div>

      <div id="value-div">
        <label for="block-value">Requirement Name:</label>
        <select id="block-value" name="name">
        <option value="CSCI-BA">ACCT-BA</option>
        <option value="CSCI-BA">CSCI-BA</option>
        <option value="CSCI-BA">CSCI-BS</option>
        <option value="CSCI-BA">LING-BA</option>
        <option value="CSCI-BA">PSYCH-BA</option>
        </select>
      </div>

      <fieldset>
        <legend>Catalog Year(s)</legend>
        <p>
          Do you want to see only the requirements for the current catalog year, the most-recent
          year (in case the program or degree is no longer being offered), or the requirements for
          all catalog years in reverse chronological order?
        </p>
        <input type="radio" id="period-all" name="period" value="all"/>
        <label for="period-all">All</label>

        <input type="radio" id="period-recent" name="period" value="recent"/>
        <label for="period-recent">Most-Recent</label>

        <input type="radio" id="period-current" name="period" value="current" checked/>
        <label for="period-current">Current</label>
        </fieldset>
      <button type="submit" id="goforit">Go For It</button>
       </div>


    </form>
    """
    return render_template('requirements_form.html',
                           result=Markup(result),
                           title='Select A Program')
  else:
    result = f"""
    {header(title='Requirements Detail',
            nav_items=[{'type': 'link',
                        'text': 'Main Menu',
                        'href': '/'}])}
    {dgw_parser(institution, b_type, b_value, period)}
    """
    return render_template('requirements.html', result=Markup(result))


@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application as Transfer Explorer.
    app.run(host='0.0.0.0', port=5000, debug=True)
