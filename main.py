# CUNY Transfer App
# C. Vickery

import sys
import os
import re
import socket

import json
import uuid
import datetime
import time

from pgconnection import pgconnection

from collections import namedtuple
from collections import defaultdict
from collections import Counter

from course_lookup import lookup_courses, lookup_course
from mysession import MySession
from sendtoken import send_token
from reviews import process_pending
from rule_history import rule_history
from format_rules import format_rule, format_rules, format_rule_by_key, institution_names, \
    Transfer_Rule, Source_Course, Destination_Course
from course_lookup import course_attribute_rows

from system_status import app_available, app_unavailable, get_reason, \
    start_update_db, end_update_db, start_maintenance, end_maintenance
from flask import Flask, url_for, render_template, make_response,\
    redirect, send_file, Markup, request, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)

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
      return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))
  else:
    return ''


# date2str()
# --------------------------------------------------------------------------------------------------
def date2str(date):
  """Takes a string in YYYY-MM-DD form and returns a text string with the date in full English form.
  """
  months = ['January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December']
  year, month, day = date.split('-')
  return '{} {}, {}'.format(months[int(month) - 1], int(day), year)


#
# Transfer App Functions
# =================================================================================================
# Map Courses: Look at rules for courses across campuses.
# Review Rules: A sequence of pages for reviewing transfer rules.
# Courses Page: Display the complete catalog of currently active courses for any college.

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


# INDEX PAGE: Top-level Menu
# =================================================================================================
# This is the entry point for the transfer application
@app.route('/', methods=['POST', 'GET'])
@app.route('/index/', methods=['POST', 'GET'])
def top_menu():
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  """ Display menu of available features.
  """
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
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
  result = """
  <div id="update-info">
    <p><sup>&dagger;</sup>{:,} transfer rules as of {}.</p>
  </div>
            """.format(num_rules, rules_date)
  return make_response(render_template('top-menu.html', result=Markup(result)))


# REVIEW_RULES PAGE
# =================================================================================================
@app.route('/review_rules/', methods=['POST', 'GET'])
def review_rules():
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  """ (Re-)establish user's mysession and dispatch to appropriate function depending on which form,
      if any, the user submitted.
  """
  if DEBUG:
    print('*** {} / ***'.format(request.method))
  mysession = MySession(request.cookies.get('mysession'))

  # Dispatcher for forms
  dispatcher = {
      'do_form_1': do_form_1,
      'do_form_2': do_form_2,
      'do_form_3': do_form_3,
  }

  if request.method == 'POST':
    # User has submitted a form.
    return dispatcher.get(request.form['next-function'], lambda: error)(request, mysession)

  # Form not submitted yet, so call do_form_0 to generate form_1
  else:
    # clear institutions, subjects, and rules from the session before restarting
    mysession.remove('source_institutions')
    mysession.remove('destination_institutions')
    mysession.remove('source_disciplines')
    mysession.remove('destination_disciplines')
    keys = mysession.keys()
    return do_form_0(request, mysession)


# do_form_0()
# -------------------------------------------------------------------------------------------------
def do_form_0(request, session):
  """
      No form submitted yet; generate the Step 1 page.
      Display form_1 to get aource and destination institutions; user's email.
  """
  if DEBUG:
    print('*** do_form_0({})'.format(session))
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

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

  source_prompt = """
    <fieldset id="sending-field"><legend>Sending College(s)</legend>
    <div id="source-college-list">
    """
  n = 0
  for code in institution_names:
    n += 1
    source_prompt += """
        <div class='institution-select'>
          <input type="checkbox" name="source" class="source" id="source-{}" value="{}">
          <label for="source-{}">{}</label>
        </div>
    """.format(n, code, n, institution_names[code])
  source_prompt += """
  </div>
  <div>
    <button type="button" id="all-sources">Select All Sending Colleges</button>
    <button type="button"  id="no-sources">Clear All Sending Colleges</button>
    </div>
  </fieldset>
  """

  destination_prompt = """
    <fieldset id="receiving-field"><legend>Receiving College(s)</legend>
    <div id="destination-college-list">
    """
  n = 0
  for code in institution_names:
    n += 1
    destination_prompt += """
        <div class='institution-select'>
          <input type="checkbox" name="destination" class="destination" id="dest-{}" value="{}">
          <label for="dest-{}">{}</label>
        </div>
    """.format(n, code, n, institution_names[code])
  destination_prompt += """
    </div>
    <div>
    <button type="button" id="all-destinations">Select All Receiving Colleges</button>
    <button type="button"  id="no-destinations">Clear All Receiving Colleges</button>
    </div>
  </fieldset>
  """

  email = ''
  if request.cookies.get('email') is not None:
    email = request.cookies.get('email')
  remember_me = ''
  if request.cookies.get('remember-me') is not None:
    remember_me = 'checked="checked"'

  # Return Form 1
  result = """
    <h1>Step 1: Select Colleges</h1>
    <div class="instructions">
      <p>
        <strong>This is the first step for reviewing the {:,}<sup>&dagger;</sup> existing course
        transfer rules at CUNY. </strong>
      </p>
      <p>
        To see just the rules you are interested in, start here by selecting exactly one sending
        college and at least one receiving college, or exactly one receiving college and one or more
        sending colleges.
        <br/>
        In the next step you will select just the discipline(s) you are interested in, and in the
        last step you will be able to review the rules that match your selections from the first two
        steps.
      </p>
      <p>
        Background information and more detailed instructions are available in the
        <a  target="_blank"
            href="https://docs.google.com/document/d/141O2k3nFCqKOgb35-VvHE_A8OV9yg0_8F7pDIw5o-jE">
            Reviewing CUNY Transfer Rules</a> document.
      </p>
    </div>
    <fieldset>
      <form method="post" action="" id="form-1">
          {}
          {}
        <fieldset>
          <legend>Your email address</legend>
          <p>
            To record your reviews of transfer rules, you need to supply a valid CUNY email address
            for verification purposes.<br/>If you just want to view the rules, you can use a dummy
            address: <em>nobody@cuny.edu</em>
          </p>
          <label for="email-text">Enter a valid CUNY email address:</label>
          <div>
            <input type="text" name="email" id="email-text" value="{}"/>
            <div>
              <input type="checkbox" name="remember-me" id="remember-me" {}/>
              <label for="remember-me"><em>Remember me on this computer.</em></label>
            </div>
          </div>
          <div id="error-msg" class="error"> </div>
          <input type="hidden" name="next-function" value="do_form_1" />
          <div>
            <button type="submit" id="submit-form-1">Next</button>
          </div>
        </fieldset>
      </form>
    </fieldset>
    <p><button><a href="/">Main Menu</a></button></p>
    <div id="update-info">
      <p><sup>&dagger;</sup>Catalog information last updated {}</p>
      <p>Transfer rules information last updated {}</p>
    </div>
    """.format(num_rules,
               source_prompt,
               destination_prompt,
               email,
               remember_me,
               catalog_date,
               rules_date)

  response = make_response(render_template('review_rules.html', result=Markup(result)))
  response.set_cookie('mysession',
                      session.session_key)

  return response


# do_form_1()
# -------------------------------------------------------------------------------------------------
def do_form_1(request, session):
  """
      Collect source institutions, destination institutions and user's email from Form 1, and add
      them to the session.
      Generate Form 2 to select discipline(s)
  """
  if DEBUG:
     print('*** do_form_1({})'.format(session))

  # Add institutions selected to user's session
  session['source_institutions'] = request.form.getlist('source')
  session['destination_institutions'] = request.form.getlist('destination')

  # Database lookups
  # ----------------
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

  # The CUNY Subjects table, for getting subject descriptions from their abbreviations
  cursor.execute("select * from cuny_subjects order by subject")
  subject_names = {row.subject: row.description for row in cursor}

  # Generate table headings for source and destination institutions
  sending_is_singleton = False
  sending_heading = 'Sending Colleges’'
  receiving_is_singleton = False
  receiving_heading = 'Receiving Colleges’'
  criterion = ''
  if len(session['source_institutions']) == 1:
    sending_is_singleton = True
    criterion = 'the sending college is ' + institution_names[session['source_institutions'][0]]
    sending_heading = '{}’s'.format(institution_names[session['source_institutions'][0]])
  if len(session['destination_institutions']) == 1:
    receiving_is_singleton = True
    receiving_heading = '{}’s'.format(institution_names[session['destination_institutions'][0]])
    if sending_is_singleton:
      criterion += ' and '
    criterion += 'the receiving college is ' + \
        institution_names[session['destination_institutions'][0]]

  # Look up all {source_institution, source_discipline, cuny_subject}
  #         and {destination_institution, destination_discipline, cuny_subject}
  # tuples for the selected source and destination institutions.

  source_institution_params = ', '.join('%s' for i in session['source_institutions'])
  q = """
  select *
     from disciplines
    where institution in ({})
    """.format(source_institution_params)
  cursor.execute(q, session['source_institutions'])
  source_disciplines = cursor.fetchall()

  destination_institution_params = ', '.join('%s' for i in session['destination_institutions'])
  q = """
  select *
     from disciplines
    where institution in ({})
    """.format(destination_institution_params)
  cursor.execute(q, session['destination_institutions'])
  destination_disciplines = cursor.fetchall()

  # The CUNY subjects actually used by the source and destination disciplines.
  cuny_subjects = set([d.cuny_subject for d in source_disciplines])
  cuny_subjects |= set([d.cuny_subject for d in destination_disciplines])
  cuny_subjects.discard('')  # empty strings don't match anything in the subjects table.
  cuny_subjects = sorted(cuny_subjects)

  cursor.close()
  conn.close()

  # Build selection list. For each cuny_subject found in either sending or receiving disciplines,
  # list all disciplines for that subject, with checkboxes for selecting either the sending or
  # receiving side.
  # The user sees College: discipline(s) in the table (source_disciplines_str), and that info is
  # encoded as a colon-separated list of college-discipline pairs (source_disciplines_val) as the
  # value of the corresponding cbox. *** TODO *** and then parse the value in do_form_2() ***
  # ===============================================================================================
  selection_rows = ''
  num_rows = 0
  for cuny_subject in cuny_subjects:

    # Sending College(s)’ Disciplines
    #   Both the college and discipline names will be displayed for each cuny_subject, unless there
    #   is only one college involved ("singleton"), in which case only the discipline name is shown.
    source_disciplines_str = ''
    source_disciplines_val = ''
    source_disciplines_set = set()
    for discipline in source_disciplines:
      if discipline.cuny_subject == cuny_subject:
        if sending_is_singleton:
          source_disciplines_set.add(discipline.discipline)
        else:
          source_disciplines_set.add((discipline.institution, discipline.discipline))
    source_disciplines_set = sorted(source_disciplines_set)

    if sending_is_singleton:
      if len(source_disciplines_set) > 1:
        source_disciplines_str = '<div>' + '</div><div>'.join(source_disciplines_set) + '</div>'
      else:
        source_disciplines_str = ''.join(source_disciplines_set)
    else:
      colleges = {}
      for discipline in source_disciplines_set:
        if discipline[0] not in colleges.keys():
          colleges[discipline[0]] = []
        colleges[discipline[0]].append(discipline[1])
      for college in colleges:
        source_disciplines_str += '<div>{}: <em>{}</em></div>'.format(institution_names[college],
                                                                      ', '.join(colleges[college]))

    # Receiving College Disciplines
    destination_disciplines_str = ''
    destination_disciplines_set = set()
    for discipline in destination_disciplines:
      if discipline.cuny_subject == cuny_subject:
        if receiving_is_singleton:
          destination_disciplines_set.add(discipline.discipline)
        else:
          destination_disciplines_set.add((discipline.institution, discipline.discipline))
    destination_disciplines_set = sorted(destination_disciplines_set)

    if receiving_is_singleton:
      destination_disciplines_str = ''
      if len(destination_disciplines_set) > 1:
        destination_disciplines_str = '<div>' + \
                                      '</div><div>'.join(destination_disciplines_set) + '</div>'
      else:
        destination_disciplines_str = ''.join(destination_disciplines_set)
    else:
      colleges = {}
      for discipline in destination_disciplines_set:
        if discipline[0] not in colleges.keys():
          colleges[discipline[0]] = []
        colleges[discipline[0]].append(discipline[1])
      for college in colleges:
        destination_disciplines_str += '<div>{}: <em>{}</em></div>'.\
            format(institution_names[college], ', '.join(colleges[college]))

    # We are showing disciplines, but reporting cuny_subjects.
    source_box = ''
    if source_disciplines_str != '':
      source_box = """
        <input type="checkbox" id="source-subject-{}" name="source_subject" value="{}"/>
        """.format(cuny_subject, cuny_subject)
    destination_box = ''
    if destination_disciplines_str != '':
      destination_box = """
        <input  type="checkbox"
                checked="checked"
                id="destination-subject-{}"
                name="destination_subject"
                value="{}"/>
        """.format(cuny_subject, cuny_subject)
    selection_rows += """
    <tr>
      <td class="source-subject"><label for="source-subject-{}">{}</label></td>
      <td class="source-subject f2-cbox">{}</td>
      <td><strong title="{}">{}</strong></td>
      <td class="destination-subject f2-cbox">{}</td>
      <td class="destination-subject"><label for="destination-subject-{}">{}</label></td>
    </tr>
    """.format(cuny_subject, source_disciplines_str,
               source_box,

               cuny_subject, subject_names[cuny_subject],

               destination_box,
               cuny_subject, destination_disciplines_str)
    num_rows += 1

  shortcuts = """
              <h2 class="error">
                There are no disciplines that match the combination of colleges you selected.
              </h2>
              """
  if num_rows > 1:
    shortcuts = """
    <table id="f2-shortcuts">
    <tr>
      <td f2-cbox" colspan="2">
        <div>
          <label for="all-source-subjects"><em>Select All Sending Disciplines: </em></label>
          <input  type="checkbox"
                  id="all-source-subjects"
                  name="all-source-subjects" />
        </div>
        <div>
          <label for="no-source-subjects"><em>Clear All Sending Disciplines: </em></label>
          <input type="checkbox" id="no-source-subjects" checked="checked"/>
        </div>
      </td>
      <td f2-cbox" colspan="2">
        <div>
          <label for="all-destination-subjects"><em>Select All Receiving Disciplines: </em>
          </label>
          <input  type="checkbox"
                  id="all-destination-subjects"
                  name="all-destination-subjects"
                  checked="checked"/>
        </div>
        <div>
          <label for="no-destination-subjects"><em>Clear All Receiving Disciplines: </em></label>
          <input type="checkbox" id="no-destination-subjects" />
        </div>
      </td>
    </tr>
    </table>
    """

  # set or clear email-related cookies based on form data
  email = request.form.get('email')
  session['email'] = email  # always valid for this session
  # The email cookie expires now or later, depending on state of "remember me"
  expire_time = datetime.datetime.now()
  remember_me = request.form.get('remember-me')
  if remember_me == 'on':
    expire_time = expire_time + datetime.timedelta(days=90)

  # Return Form 2
  result = """
  <h1>Step 2: Select Sending &amp; Receiving Disciplines</h1>
  <div class="instructions">
    <strong>There are {:,} disciplines where {}.</strong><br/>
    Disciplines are grouped by CUNY subject area.<br/>
    Select at least one sending discipline and at least one receiving discipline.<br/>
    By default, all receiving disciplines are selected to account for all possible equivalencies,
    including electives and blanket credit.<br/>
    The next step will show all transfer rules for courses in the corresponding pairs of
    disciplines.<br/>
    <strong>
      Clicking on these instructions hides them, making more room for the list of subjects.
    </strong>
  </div>
  <form method="post" action="" id="form-2">
    <a href="/" class="restart">Main Menu</a>
    <a href="/review_rules" class="restart">Restart</a>
    <button type="submit">Next</button>
    <input type="hidden" name="next-function" value="do_form_2" />
    {}
    <div id="subject-table-div" class="selection-table-div">
      <table id="subject-table">
        <thead>
          <tr>
            <th class="source-subject">{} Discipline(s)</th>
            <th class="source-subject">Select Sending</th>
            <th>CUNY Subject</th>
            <th class="destination-subject">Select Receiving</th>
            <th class="destination-subject">{} Discipline(s)</th>
          </tr>
        </thead>
        <tbody>
        {}
        </tbody>
      </table>
    </div>
  </form>
  """.format(len(source_disciplines) + len(destination_disciplines), criterion,
             shortcuts, sending_heading, receiving_heading, selection_rows)
  response = make_response(render_template('review_rules.html', result=Markup(result)))
  response.set_cookie('email', email, expires=expire_time)
  response.set_cookie('remember-me', 'on', expires=expire_time)
  return response


# do_form_2()
# -------------------------------------------------------------------------------------------------
def do_form_2(request, session):
  """
      Process CUNY Subject list from form 2.
      Generate form_3: the selected transfer rules for review
  """
  if DEBUG:
    print(f'*** do_form_2()')
    elapsed = time.perf_counter()
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

  # Look up transfer rules where the sending course belongs to a sending institution and is one of
  # the source disciplines and the receiving course belongs to a receiving institution and is one of
  # the receiving disciplines.
  try:
    source_institution_params = ', '.join('%s' for i in session['source_institutions'])
    destination_institution_params = ', '.join('%s' for i in session['destination_institutions'])
  except KeyError:
    # the session is expired or invalid. Go back to Step 1.
    return render_template('review_rules.html', result=Markup("""
                                                           <h1>Session Expired</h1>
                                                           <p>
                                                             <a href="/">
                                                                <button>Main Menu</button></a>
                                                             <a href="/review_rules"
                                                                  class="restart">Restart
                                                              </a>
                                                           </p>

                                                           """))

  # Be sure there is the possibility there will be some rules
  source_subject_list = request.form.getlist('source_subject')
  destination_subject_list = request.form.getlist('destination_subject')

  if len(source_subject_list) < 1:
    return render_template('review_rules.html', result=Markup(
                           '<h1 class="error">No sending disciplines selected.</h1>'))
  if len(destination_subject_list) < 1:
    return render_template('review_rules.html', result=Markup(
                           '<h1 class="error">No receiving disciplines selected.</h1>'))

  # Prepare the query to get the set of rules that match the institutions and cuny_subjects
  # selected.
  if request.form.get('all-source-subjects'):
    source_subject_clause = ''
  else:
    source_subjects_str = '|'.join(f':{s}:' for s in source_subject_list)
    source_subjects_clause = f"  and '{source_subjects_str}' ~ source_subjects"
    source_subjects = ', '.join(f"'{s}'" for s in source_subject_list)
    source_subjects_clause = f"""
      and id in (select rule_id from subject_rule_map where subject in ({source_subjects}))"""

  # Get all the rules where,
  #  - The source and destination institutions have been selected
  #  and
  #  - The source_subjects have been selected
  if DEBUG:
    elapsed = time.perf_counter() - elapsed
    print(f'*** start get rules:\t{elapsed:0.3f}')
  q = f"""
  select *
    from transfer_rules
   where source_institution in (%s)
     and destination_institution in (%s)
     {source_subjects_clause}
  order by source_institution, destination_institution, subject_area, group_number"""
  cursor.execute(q, (session['source_institutions'] + session['destination_institutions']))

  if cursor.rowcount < 1:
    return render_template('review_rules.html', result=Markup(
                           '<h1 class="error">There are no matching rules.</h1>'))

  all_rules = cursor.fetchall()
  selected_rules = []
  # Get the source and destination course lists from the above set of rules where the destination
  # subject was selected. It's possible to have selected rules that don’t transfer to any of the
  # selected destination subjects, so those rules are dropped while building the selected-rules
  # list.
  if request.form.get('all-destination-subjects'):
    destination_subjects_clause = ''
  else:
    # Create a clause that makes sure the destination course has one of the destination subjects
    destination_subject_list = request.form.getlist('destination_subject')
    destination_subject_params = ', '.join(f"'{s}'" for s in destination_subject_list)
    destination_subjects_clause = f" and dc.cuny_subject in ({destination_subject_params})"

  for rule in all_rules:
    if DEBUG:
      elapsed = time.perf_counter() - elapsed
      print(f'*** start get destination courses for rule \t{rule.id}: {elapsed:0.3f}')
    # It’s possible some of the selected rules don’t have destination courses in any of the selected
    # disciplines, so that has to be checked first.
    cursor.execute(f"""
      select  dc.course_id,
              dc.offer_count,
              dc.discipline,
              dc.catalog_number,
              dc.cat_num,
              dc.cuny_subject,
              dc.transfer_credits,
              dn.description
      from destination_courses dc, disciplines dn
      where dc.rule_id = %s
        and dn.institution = %s
        and dn.discipline = dc.discipline
        {destination_subjects_clause}
       order by discipline, cat_num
    """, (rule.id, rule.destination_institution))
    if cursor.rowcount > 0:
      destination_courses = [Destination_Course._make(c) for c in cursor.fetchall()]
      if DEBUG:
        elapsed = time.perf_counter() - elapsed
        print(f'*** start get source courses for rule\t\t{rule.id}: {elapsed:0.3f}')
      cursor.execute("""
        select  sc.course_id,
                sc.offer_count,
                sc.discipline,
                sc.catalog_number,
                sc.cat_num,
                sc.cuny_subject,
                sc.min_credits,
                sc.max_credits,
                sc.min_gpa,
                sc.max_gpa,
                dn.description
        from source_courses sc, disciplines dn
        where sc.rule_id = %s
          and dn.institution = %s
          and dn.discipline = sc.discipline
        order by discipline, cat_num
        """, (rule.id, rule.source_institution))
      if cursor.rowcount > 0:
        source_courses = [Source_Course._make(c)for c in cursor.fetchall()]
      if DEBUG:
        elapsed = time.perf_counter() - elapsed
        print(f'*** end get source courses for rule\t\t{rule.id}: {elapsed:0.3f}')

      # Create the Transfer_Rule tuple suitable for passing to format_rules, and add it to the
      # list of rules to pass.
      selected_rules.append(Transfer_Rule._make(
          [rule.id,
           rule.source_institution,
           rule.destination_institution,
           rule.subject_area,
           rule.group_number,
           rule.source_disciplines,
           rule.source_subjects,
           rule.review_status,
           source_courses,
           destination_courses]))
  cursor.close()
  conn.close()

  if len(selected_rules) == 0:
    num_rules = 'No matching transfer rules found.'
  if len(selected_rules) == 1:
    num_rules = 'There is one matching transfer rule.'
  if len(selected_rules) > 1:
    num_rules = 'There are {:,} matching transfer rules.'.format(len(selected_rules))

  rules_table = format_rules(selected_rules)

  result = f"""
  <h1>Step 3: Review Transfer Rules</h1>
    <div class="instructions">
      <strong>{num_rules}</strong><br/>
      Rules that are <span class="credit-mismatch">highlighted like this</span> have a different
      number of credits taken from the number of credits transferred.
      Hover over the “=>” to see the numbers of credits.<br/>
      Credits in parentheses give the number of credits transferred where that does not match the
      nominal number of credits for a course.<br/>
      Rules that are <span class="evaluated">highlighted like this</span> are ones that you have
      reviewed but not yet submitted.<br/>
      Click on a rule to review it.<br/>
      <strong>
        Clicking on these instructions hides them, making more room for the list of rules.
      </strong>
    </div>
    <p>
      <a href="/"><button>Main Menu</button></a>
      <a href="/review_rules" class="restart">Restart</a>
    </p>
    <fieldset id="verification-fieldset">
        <p id="num-pending">You have not reviewed any transfer rules yet.</p>
        <button type="text" id="send-email" disabled="disabled">
        Preview Your Submissions
      </button>
      <form method="post" action="" id="review-form">
        Waiting for rules to finish loading ...
      </form>
    </fieldset>
    <div id="rules-table-div" class="selection-table-div">
    {rules_table}
    </div>
  """
  if DEBUG:
    elapsed = time.perf_counter() - elapsed
    print(f'*** return:\t{elapsed:0.3f}')
  return render_template('review_rules.html', result=Markup(result))


# do_form_3()
# -------------------------------------------------------------------------------------------------
def do_form_3(request, session):
  if DEBUG:
      print('*** do_form_3({})'.format(session))
  reviews = json.loads(request.form['reviews'])
  kept_reviews = [e for e in reviews if e['include']]
  email = session['email']
  if len(kept_reviews) == 0:
    result = '<h1>There are no reviews to confirm.</h1>'
  else:
    message_tail = 'review'
    if len(kept_reviews) > 1:
      num_reviews = len(kept_reviews)
      if num_reviews < 13:
        num_reviews = ['two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                       'eleven', 'twelve'][num_reviews - 2]
      message_tail = '{} reviews'.format(num_reviews)

    # Insert these reviews into the pending_reviews table of the db.
    conn = pgconnection('dbname=cuny_courses')
    cursor = conn.cursor()
    token = str(uuid.uuid4())
    reviews = json.dumps(kept_reviews)
    q = "insert into pending_reviews (token, email, reviews) values(%s, %s, %s)"
    cursor.execute(q, (token, email, reviews))
    conn.commit()
    conn.close()

    # Description message templates
    review_dict = dict()
    review_dict['ok'] = '{}: OK'
    review_dict['not-ok'] = '{}: {}'
    review_dict['other'] = 'Other: {}'

    # Generate description messages
    style_str = ' style="border:1px solid #666;vertical-align:top; padding:0.5em;"'
    suffix = 's'
    if len(kept_reviews) == 1:
      suffix = ''
    review_rows = """
                      <table style="border-collapse:collapse;">
                        <tr>
                          <th colspan="5"{}>Rule</th>
                          <th{}>Your Review{}</th>
                        </tr>
                        """.format(style_str, style_str, suffix)
    for review in kept_reviews:
      event_type = review['event_type']
      if event_type == 'src-ok':
          description = review_dict['ok'].format(re.sub(r'\d+', '',
                                                        review['source_institution']))
      elif event_type == 'dest-ok':
        description = review_dict['ok'].format(re.sub(r'\d+', '',
                                                      review['destination_institution']))
      elif event_type == 'src-not-ok':
        description = review_dict['not-ok'].format(re.sub(r'\d+', '',
                                                          review['source_institution']),
                                                   review['comment_text'])
      elif event_type == 'dest-not-ok':
        description = review_dict['not-ok'].format(re.sub(r'\d+', '',
                                                          review['destination_institution']),
                                                   review['comment_text'])
      else:
        description = review_dict['other'].format(review['comment_text'])

      rule_str = re.sub(r'</tr>',
                        """<td>{}</td></tr>
                        """.format(description), review['rule_str'])
      review_rows += re.sub('<td([^>]*)>', '<td\\1{}>'.format(style_str), rule_str)
    review_rows += '</table>'
    # Send the email
    hostname = os.environ.get('HOSTNAME')
    if hostname == 'babbage.cs.qc.cuny.edu' or (hostname and hostname.endswith('.local')):
      hostname = 'http://localhost:5000'
    else:
      hostname = 'https://provost-access-148820.appspot.com'
    url = hostname + '/confirmation/' + token

    response = send_token(email, url, review_rows)
    if response.status_code != 202:
      result = 'Error sending email: {}'.format(response.body)
    else:
      result = """
      <h1>Step 4: Respond to Email</h1>
      <p>
        Check your email at {}.<br/>Click on the 'activate these reviews' button in that email to
        confirm that you actually wish to have your {} recorded.
      </p>
      <p>
        Thank you for your work!
      </p>
      <a href="/"><button>Main Menu</button></a>
      <a href="/review_rules" class="restart">Restart</a>

      """.format(email, message_tail)
  return render_template('review_rules.html', result=Markup(result))


# PENDING PAGE
# -------------------------------------------------------------------------------------------------
@app.route('/pending')
def pending():
  """ Display pending reviews.
      TODO: Implement login option so defined users can manage this table.
  """
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  cursor.execute("""
    select email, reviews, to_char(when_entered, 'Month DD, YYYY HH12:MI am') as when_entered
      from pending_reviews""")
  rows = ''
  for pending in cursor.fetchall():
    rows += format_pending(pending)
  cursor.close()
  conn.close()

  if rows == '':
    table = '<h2>There are no pending reviews.</h2>'
  else:
    table = '<table>{}</table>'.format(rows)
  result = """
  <h1>Pending Reviews</h1>
  {}
  <p><a href="/"><button>main menu</button></a></p>
  """.format(table)
  return render_template('review_rules.html', result=Markup(result))


# format_pending()
# -------------------------------------------------------------------------------------------------
def format_pending(item):
  """ Generate a table row that describes pending reviews.
  """
  reviews = json.loads(item['reviews'])
  suffix = 's'
  if len(reviews) == 1:
    suffix = ''
  return """<tr><td>{} review{} by {} on {}</td></tr>
  """.format(len(reviews), suffix, item['email'], item['when_entered'])


# CONFIRMATION PAGE
# -------------------------------------------------------------------------------------------------
# This is the handler for clicks in the confirmation email.
@app.route('/confirmation/<token>', methods=['GET'])
def confirmation(token):
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  # Make sure the token is received and is in the pending table.
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  q = 'select * from pending_reviews where token = %s'
  cursor.execute(q, (token,))
  rows = cursor.fetchall()
  cursor.close()
  conn.close()

  msg = ''
  if len(rows) == 0:
    msg = '<p class="error">This report has either expired or already been recorded.</p>'
  if len(rows) > 1:
    msg = '<p class="error">Program Error: multiple pending_reviews.</p>'
  if len(rows) == 1:
    msg = process_pending(rows[0])
  result = """

  <h1>Confirmation</h1>
  <p>Review Report ID: {}</p>
  {}
    """.format(token, msg)
  return render_template('review_rules.html', result=Markup(result))


# HISTORY PAGE
# -------------------------------------------------------------------------------------------------
# Display the history of review events for a rule.
#
@app.route('/history/<rule>', methods=['GET'])
def history(rule):
  if app_unavailable():
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  """ Look up all events for the rule, and report back to the visitor.
  """
  result = rule_history(rule)
  return render_template('review_rules.html', result=Markup(result))


# # LOOKUP PAGE
# # -------------------------------------------------------------------------------------------------
# # Lookup all the rules that involve a course.
# # This page is not used any more. Map Courses does the job better.
# # Also, deleting the regex tutorial.
# @app.route('/lookup', methods=['GET'])
# def lookup():
#   """ Prompt for a course (or set of courses in a discipline) at an institution, and display
#       view-only information about rules that involve that or those courses.
#   """
#   conn = pgconnection('dbname=cuny_courses')
#   cursor = conn.cursor()
#   cursor.execute('select code, prompt from institutions order by prompt')
#   options = ['<option value="{}">{}</option>'.format(x[0], x[1]) for x in cursor.fetchall()]
#   conn.close()
#   institution_select = """
#   <select id="institution" name="institution">
#     <option value="none" selected="selected">Select a College</option>
#     {}
#   </select>
#   """.format('\n'.join(options))
#   # Supply colleges from db now, but use ajax to get a college's disciplines

#   result = """
#   <h1>Lookup Transfer Rules</h1>
#   <div class="instructions">
#     <p>
#       Select a college and discipline, and enter a course catalog number to see what transfer
#       rules involve that course CUNY-wide. You can limit the search to rules where the course is
#       on the sending instituion side or the receiving institution side, or leave the default and
#       get both sets.
#     </p>
#     <p>
#       The Catalog Number field can be entered as a simple course number but is actually a ”regular
#       expression” that can select a group of courses. So if you wanted to do something like find the
#       rules for all 100-level courses in a discipline, you might want to look at the <a
#       href="/regex" target="_blank">regular expression</a> web page for more information about this
#       field. And if you enter a simple course number but get back information for some additional
#       courses, that web page explains what’s going on in that case, too.
#     </p>
#   </div>
#   <form action="" method="POST">
#     <div>
#       <label for="institution">College:</label>
#       {}
#     </div>
#     <div>
#       <label for="Discipline">Discipline:</label>
#       <input type="text" id="discipline" />
#     </div>
#     <div>
#       <label for="catalog-number">Catalog Number:</label>
#       <input type="text" id="catalog-number" />
#     </div>
#     <div id="radios">
#       <div>
#         <input type="radio" id="sending-only" name="which-rules" value="1">
#         <label for="sending-only" class="radio-label">Sending Rules Only</label>
#       </div>
#       <div>
#         <input type="radio" id="receiving-only" name="which-rules" value="2">
#         <label for="receiving-only" class="radio-label"">Receiving Rules Only</label>
#       </div>
#       <div>
#         <input type="radio" id="both" name="which-rules" value="3" checked="checked">
#         <label for="both" class="radio-label">Both Sending and Receiving Rules
#         </label>
#       </div>
#     </div>
#   </form>
#   <hr>
#   <h2>Sending Rules</h2>
#   <div id="sending-rules">
#   </div>
#   <h2>Receiving Rules</h2>
#   <div id="receiving-rules">
#   </div>
#   """.format(institution_select)
#   return render_template('lookup.html', result=Markup(result))


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
    return make_response(render_template('app_unavailable.html', result=Markup(get_reason())))

  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
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

  result = """
  <h1>Map Course Transfers</h1>
  <div id="setup-div">
    <h2>Setup</h2>
    <div class="instructions">
      <p>
        Select courses of interest, then indicate whether you want to map how these courses transfer
        <em>to</em> courses at other institutions (<em>receiving</em> courses) or <em>from</em>
        courses at other institutions (<em>sending courses</em>).
      </p>
    </div>
    <form action="" method="POST">
      <fieldset>
        <h2>
          Select one or more of the following groups of courses.
        </h2>
        <div id="grouping-div">
          <label for="course-groups">Groups:</label>
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
            <em>Note:</em> Catalog numbers greater than 999 will be divided by ten until they are
            in the range 0 to 999 for grouping purposes.
          </p>
        </div>
        <h2>
          Select a college and the discipline for the courses you are interested in.
        </h2>
        <div>
          <label for="institution">College:</label>
          {}
          <span id="discipline-span">
            <label for="Discipline">Discipline:</label>
            <input type="text" id="discipline" />
          </span>
        </div>
      </fieldset>

      <p>
        <span id="num-courses">No courses</span> selected.
      </p>
      <div>
        <button id="show-receiving">show receiving courses</button>
        <strong>or</strong>
        <button id="show-sending">show sending courses</button>
        <span id="loading">Loading
          <span class="one">.</span>
          <span class="two">.</span>
          <span class="three">.</span>
        </span>
      </div>
      <div>
          <input  type="checkbox"
                  id="associates"
                  name="which-colleges"
                  value="assocociates"
                  checked>
          <label for="associates" class="radio-label">Include Associates Degree Colleges</label>
          <input  type="checkbox"
                  id="bachelors"
                  name="which-colleges"
                  value="bachelors"
                  checked>
          <label for="bachelors" class="radio-label"">Include Bachelor’s Degree Colleges</label>
      </div>
    </form>
  </div>
  <div id="transfers-map-div">
    <h2>Transfers Map</h2>
    <div class="instructions">
      <p>
        Each row of the table below shows the number of ways each course selected during setup
        transfers <span id="map-direction">to</span> other CUNY colleges.
      </p>
      <p>
        If a cell contains zero there are no transfer rules for the course and that college. Values
        greater than one occur when there are multiple rules, for example when a course transfers as
        a particular destination course only if the student earned a minimum grade, and as blanket
        credit otherwise.
      </p>
      <p>
        If a course is<span class="inactive-course"> highlighted like this, </span>it is inactive,
        and non-zero rule counts are<span class="bogus-rule"> highlighted like this.</span> If this
        is a sending course, it is possible the rule would be used for students who completed the
        course before it became inactive. But if this is a receiving course, the rule is definitely
        an error.
      </p>
      <p>
        If the table is empty, it means that all the selected courses are inactive and there are no
        transfer rules for them with any college. (A good thing.)
      </p>
      <p>
        If a course is active but has zero values for some colleges, they are<span
        class="missing-rule"> highlighted like this.</span>
      </p>
      <p>
        If a course transfers only as blanket credit, it is <span class="blanket-credit">highlighted
        like this.</span>
      </p>
      <p>
        If there are any rules that maps courses to their own institution, they are<span
        class="self-rule"> highlighted like this.</span>
      </p>
      <p>
        Click on courses to see their catalog information. Click on non-zero cells to see details
        about those rule(s).
      </p>
      <p class="hide-show">
        Click anywhere in these instructions to hide them.<br>
        Type a question mark to see them again.
      </p>
    </div>
    <table id="transfers-map-table">
    </table>
    <div>
      <a href="/"><button>main menu</button></a>
      <button id="show-setup">return to setup</button>
    </div>
  </div>
  <div id="pop-up-div">
    <div id="pop-up-container">
      <div id="dismiss-bar">x</div>
      <div id="pop-up-content"></div>
    </div>
  </div>
  """.format(institution_select)
  return render_template('map-courses.html', result=Markup(result))


# /_INSTITUTIONS
# =================================================================================================
# AJAX access to the institutions table.
@app.route('/_institutions')
def _institutions():
  Institution = namedtuple('Institution', 'code, prompt, name, associates, bachelors')
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
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
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  cursor.execute("""select discipline
                      from disciplines
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
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
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

  request_type = request.args.get('request_type', default='show-receiving')

  table_rows = []
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
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
                         <th class="clickable {}" title="course_id {}: {} {}"{}>{} {} {}</th>
                       """.format(class_info,
                                  course_info.course_id,
                                  course_info.institution,
                                  course_info.title,
                                  class_info,
                                  course_info.institution.rstrip('0123456789'),
                                  course_info.discipline,
                                  course_info.catalog_number)
    # Collect rules where the selected course is a sending course
    if request_type == 'show-receiving':
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
      if request_type == 'show-receiving':
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
      data_cells += '<td title="{}"{}>{}</td>'.format(rules_str, class_info, num_rules)
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
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
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


# /_SESSIONS
# =================================================================================================
# This route is intended as a utility for pruning dead "mysession" entries from the db. A periodic
# script can access this url to prevent db bloat when millions of people start using the app. Until
# then, it's just here in case it's needed.
@app.route('/_sessions')
def _sessions():
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  q = 'select session_key, expiration_time from sessions order by expiration_time'
  cursor.execute(q)
  result = '<table>'
  now = datetime.datetime.now()
  num_expired = 0
  for row in cursor.fetchall():
    ts = datetime.datetime.fromtimestamp(row['expiration_time'])
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

  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  num_active_courses = 0
  if request.method == 'POST':
    institution_code = request.form['inst']
  else:
    institution_code = request.args.get('college')
  if institution_code:
    cursor.execute("""
              select name, date_updated
                from institutions
               where code ~* %s
               """, (institution_code,))
    if cursor.rowcount == 1:
      # Found a college: assuming it offers some courses
      row = cursor.fetchone()
      institution_name = row.name
      date_updated = row.date_updated.strftime('%B %d, %Y')
      cursor.execute("""
          select count(*) from courses
           where institution ~* %s
             and course_status = 'A'
             and can_schedule = 'Y'
             and discipline_status = 'A'
          """, [institution_code])
      num_active_courses = cursor.fetchone()[0]

      result = """
        <h1>{} Courses</h1>
        <div class="instructions">
          <p class='subtitle'>{:,} active courses as of {}</p>
          <p>
            <em>
              The following course properties are shown in parentheses following the catalog
              description:
            </em>
          </p>
          <ul>
            <li title="CUNYfirst uses “career” to mean undergraduate, graduate, etc.">Career;</li>
            <li title="CUNY-standard name for the academic discipline">CUNY Subject;</li>
            <li title="Each course has exactly one Requirement Designation (RD).">
              Requirement Designation;</li>
            <li id="show-attributes"
                title="A course can have any number of attributes. Click here to see descriptions.">
              Course Attributes (a comma-separated list of name:value attribute pairs).
            </li>
          </ul>
          <em>Hover over above list for more information.</em>
          <br><em>Click to hide these instructions. Type ? to get them back.</em>
          <div id="pop-up-div">
            <div id="pop-up-inner">
              <div id="dismiss-bar">x</div>
              <table>
                <tr><th>Name</th><th>Value</th><th>Description</th></tr>
                {}
              </table>
            </div>
          </div>
        </div>
        <p id="need-js" class="error">Loading catalog information ...</p>
        """.format(institution_name, num_active_courses, date_updated, course_attribute_rows)
      result = result + lookup_courses(institution_code)

  if num_active_courses == 0:
    # No courses yet (bogus or missing institution): prompt user to select an institution
    prompt = """
    <h1>List Active Courses</h1><p>Pick a college and say “Please”.</p>
    <fieldset><legend>Select a College</legend>"""
    cursor.execute("select * from institutions order by code")
    n = 0
    for row in cursor:
      n += 1
      prompt = prompt + """
      <div class='institution-select'>
        <input type="radio" name="inst" id="inst-{}" value="{}">
        <label for="inst-{}">{}</label>
      </div>
      """.format(n, row.code, n, row.name)
    result = """
    <p id="need-js" class="error">This app requires JavaScript.</p>
    <form method="post" action="">
      {}
      <div>
        <button type="submit">Please
        </button>
      </div>
    <form>
    """.format(prompt)
  cursor.close()
  conn.close()
  return render_template('courses.html', result=Markup(result))


# # /REGEX obsoletificization.
# # ================================================================================================
# # A help page for entering regular expressions as course catalog numbers.
# @app.route('/regex')
# def regex():
#   return render_template('regex.html')


@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='0.0.0.0', port=5000, debug=True)
