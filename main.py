import logging
import sys
import os
import re
import socket

import json
import uuid
import datetime, time

from pgconnection import pgconnection

import logging

from collections import namedtuple

from cuny_course import CUNYCourse
from mysession import MySession
from sendtoken import send_token
from evaluations import process_pending, rule_history, status_string
from extract_groups import extract_groups

from flask import Flask, url_for, render_template, make_response,\
                  redirect, send_file, Markup, request, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)

#
# Initialization

Filter = namedtuple('Filter', ['subject', 'college', 'discipline'])

logger = logging.getLogger('debugging')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('debugging.log')
sh = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
#logger.addHandler(fh)
logger.addHandler(sh)
logger.debug('Debug: App Start')

#
# Overhead URIs
@app.route('/favicon.ico')
def favicon():
  return send_file('favicon.ico', mimetype = "image/x-icon")

@app.route('/image/<file_name>')
def image_file(file_name):
  return send_file('static/images/' + file_name + '.png')

def error():
  result = "<h1>Error</h1>"
  return render_template('transfers.html', result=Markup(result))


# QC Applications
# =================================================================================================
# Index: Require user to sign in using  QC email address, and provide a menu of applications.
# Assessment: Demonstrate accessing G-Suite Assessment repository info.

# INDEX
# -------------------------------------------------------------------------------------------------
@app.route('/')
@app.route('/index')
def index():
  return render_template('index.html')

# ASSESSMENT
# -------------------------------------------------------------------------------------------------
@app.route('/assessment')
def assessment():
  return render_template('assessment.html')


#
# CUNY Applications
# =================================================================================================
# Transfer Pages: A sequence of pages for reviewing transfer rules.
# Courses Page: Display the complete catalog of currently active courses for any college.

# TRANSFERS PAGES
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

# do_form_0()
# -------------------------------------------------------------------------------------------------
def do_form_0(request, session):
  """
      No form submitted yet; generate the Step 1 page.
      Display form_1 to get aource and destination institutions; user's email.
  """
  logger.debug('*** do_form_0({})'.format(session))
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  cursor.execute("select * from institutions order by lower(name)")
  institution_list = cursor.fetchall()
  cursor.close()
  conn.close()

  source_prompt = """
    <fieldset id="sending-field"><legend>Sending College(s)</legend>
    <div id="source-college-list">
    """
  n = 0
  for row in institution_list:
    n += 1
    source_prompt += """
        <div class='institution-select'>
          <input type="checkbox" name="source" class="source" id="source-{}" value="{}">
          <label for="source-{}">{}</label>
        </div>
    """.format(n, row['code'], n, row['name'])
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
  for row in institution_list:
    n += 1
    destination_prompt += """
        <div class='institution-select'>
          <input type="checkbox" name="destination" class="destination" id="dest-{}" value="{}">
          <label for="dest-{}">{}</label>
        </div>
    """.format(n, row['code'], n, row['name'])
  destination_prompt += """
    </div>
    <div>
    <button type="button" id="all-destinations">Select All Receiving Colleges</button>
    <button type="button"  id="no-destinations">Clear All Receiving Colleges</button>
    </div>
  </fieldset>
  """
  destination_disciplines_prompt = "<fieldset><legend>Discipline/Subject(s)</legend>"
  destination_disciplines_prompt += "</fieldset>"

  email = ''
  if request.cookies.get('email') != None:
    email = request.cookies.get('email')
  remember_me = ''
  if request.cookies.get('remember-me') != None:
    remember_me = 'checked="checked"'

  # Return Form 1
  result = """
    <h1>Step 1: Select Colleges</h1>
    <p>
      This is the first step of a web application for reviewing course transfer rules at CUNY.<br/>
      Background information and instructions are available in the
      <a
        href="https://docs.google.com/document/d/141O2k3nFCqKOgb35-VvHE_A8OV9yg0_8F7pDIw5o-jE/edit?usp=sharing">
        CUNY Transfer Rules Evaluation</a> document.
    <fieldset>
      <form method="post" action="" id="form-1">
          {}
          {}
        <fieldset>
          <legend>Your email address</legend>
          <label for="email-text">Enter a valid CUNY email address:</label>
          <div>
            <input type="text" name="email" id="email-text" value="{}"/>
            <div>
              <input type="checkbox" name="remember-me" id="remember-me" {}/>
              <label for="remember-me"><em>Remember me on this computer.</em></label>
            </div>
          </div>
          <div>
            <div id="error-msg" class="error"> </div>
            <input type="hidden" name="next-function" value="do_form_1" />
            <button type="submit" id="submit-form-1">Next</button>
          </div>
        </fieldset>
      </form>
    </fieldset>
    """.format(source_prompt, destination_prompt, email, remember_me)

  response = make_response(render_template('transfers.html', result=Markup(result)))
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
  logger.debug('*** do_form_1({})'.format(session))

  # Capture form data in user's session
  session['source_institutions'] = request.form.getlist('source')
  session['destination_institutions'] = request.form.getlist('destination')

  # Database lookups
  # ----------------
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

  # Look up source and destination institiution names
  cursor.execute("select * from institutions order by code")
  institution_names = {row['code']: row['name'] for row in cursor}

  # The CUNY Subjects table, for getting subject descriptions from their abbreviations
  cursor.execute("select * from cuny_subjects order by subject")
  subject_names = {row['subject']:row['description'] for row in cursor}

  # Generate table headings for source and destination institutions
  sending_is_singleton = False
  sending_heading = 'Sending Colleges’'
  receiving_is_singleton = False
  receiving_heading ='Receiving Colleges’'
  criterion = ''
  if len(session['source_institutions']) == 1:
    sending_is_singleton = True
    criterion = 'the sending college is ' + institution_names[session['source_institutions'][0]]
    sending_heading = '{}’s'.format(institution_names[session['source_institutions'][0]])
  if len(session['destination_institutions']) == 1:
    receiving_is_singleton = True
    receiving_heading = '{}’s'.format(institution_names[session['destination_institutions'][0]])
    if sending_is_singleton: criterion += ' or '
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
  Discipline = namedtuple('Discipline', [d[0] for d in cursor.description])
  source_disciplines = [discipline for discipline in map(Discipline._make, cursor.fetchall())]

  destination_institution_params = ', '.join('%s' for i in session['destination_institutions'])
  q = """
  select *
     from disciplines
    where institution in ({})
    """.format(destination_institution_params)
  cursor.execute(q, session['destination_institutions'])
  destination_disciplines = [discipline for discipline in map(Discipline._make, cursor.fetchall())]

  # The CUNY subjects actually used by the source and destination disciplines.
  subjects = set([d.cuny_subject for d in source_disciplines])
  subjects |= set([d.cuny_subject for d in destination_disciplines])
  subjects.discard('') # empty strings don't match anything in the subjects table.
  subjects = sorted(subjects)

  cursor.close()
  conn.close()

  # Build selection list. For each cuny_subject found in either sending or receiving disciplines,
  # list all disciplines for that subject, with checkboxes for selecting either the sending or
  # receiving side.
  # ===============================================================================================
  selection_rows = ''
  num_rows = 0
  for subject in subjects:
    # Sending College Disciplines
    source_disciplines_str = ''
    source_disciplines_set = set()
    for discipline in source_disciplines:
      if discipline.cuny_subject == subject:
        if sending_is_singleton:
          source_disciplines_set.add(discipline.discipline)
        else:
          source_disciplines_set.add((discipline.institution, discipline.discipline))
    source_disciplines_set = sorted(source_disciplines_set)

    if sending_is_singleton:
      if len(source_disciplines_set) > 1:
        source_disciplines_str = '<div>' +'</div><div>'.join(source_disciplines_set) + '</div>'
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
      if discipline.cuny_subject == subject:
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
        destination_disciplines_str += '<div>{}: <em>{}</em></div>'.format(institution_names[college],
                                                                       ', '.join(colleges[college]))

    source_box = ''
    if source_disciplines_str != '':
      source_box = """
        <input type="checkbox" id="source-subject-{}" name="source_subject" value="{}"/>
        """.format(subject, subject)
    destination_box = ''
    if destination_disciplines_str != '':
      destination_box = """
        <input type="checkbox" id="destination-subject-{}" name="destination_subject" value="{}"/>
        """.format(subject, subject)
    selection_rows += """
    <tr>
      <td class="source-subject"><label for="source-subject-{}">{}</label></td>
      <td class="source-subject f2-cbox">{}</td>
      <td><strong>{}</strong></td>
      <td class="destination-subject f2-cbox">{}</td>
      <td class="destination-subject"><label for="destination-subject-{}">{}</label></td>
    </tr>
    """.format(
               subject, source_disciplines_str,
               source_box,

               subject_names[subject],

               destination_box,
               subject, destination_disciplines_str)
    num_rows += 1

  if num_rows > 1:
    shortcuts = """
    <table id="f2-shortcuts">
    <tr>
      <td class="source-subject f2-cbox" colspan="2">
        <div>
          <label for="all-sending-subjects"><em>Select All Sending Disciplines: </em></label>
          <input type="checkbox" id="all-sending-subjects" />
        </div>
        <div>
          <label for="no-sending-subjects"><em>Clear All Sending Disciplines: </em></label>
          <input type="checkbox" id="no-sending-subjects" />
        </div>
      </td>
      <td class="destination-subject f2-cbox" colspan="2">
        <div>
          <label for="all-receiving-subjects"><em>Select All Receiving Disciplines: </em></label>
          <input type="checkbox" id="all-receiving-subjects" />
        </div>
        <div>
          <label for="no-receiving-subjects"><em>Clear All Receiving Disciplines: </em></label>
          <input type="checkbox" id="no-receiving-subjects" />
        </div>
      </td>
    </tr>
    </table>
    """

  # set or clear email-related cookies based on form data
  email = request.form.get('email')
  session['email'] = email # always valid for this session
  # The email cookie expires now or later, depending on state of "remember me"
  expire_time = datetime.datetime.now()
  remember_me = request.form.get('remember-me')
  if remember_me == 'on':
    expire_time = expire_time + datetime.timedelta(days=90)

  result = """
  <h1>Step 2: Select CUNY Subjects</h1>
  <div class="instructions">
    There are {:,} disciplines where {}.<br/>
    Disciplines are grouped by CUNY subject area.<br/>
    Select at least one sending discipline and at least one receiving discipline.<br/>
    The next step will show all transfer rules for courses in the corresponding pairs of
    disciplines.<br/>
    <em>Click on these instructions to remove them.</em>
  </div>
  <form method="post" action="" id="form-2">
    <a href="/review_transfers/" class="restart">Restart</a>
    <button type="submit">Next</button>
    <input type="hidden" name="next-function" value="do_form_2" />
    {}
    <div id="subject-table-div">
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
  response = make_response(render_template('transfers.html', result=Markup(result)))
  response.set_cookie('email', email, expires=expire_time)
  response.set_cookie('remember-me', 'on', expires=expire_time)
  return response

# do_form_2()
# -------------------------------------------------------------------------------------------------
def do_form_2(request, session):
  """
      Process CUNY Subject list from form 2 and add to session.
      Generate form_3: the selected transfer rules for evaluation
  """
  logger.debug('*** do_form_2({})'.format(session))
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()

  # Look up transfer rules where the sending course belongs to a sending institution and is one of
  # the source subjects and the receiving course belongs to a receiving institution and is one of
  # the receiving subjects.
  try:
    source_institution_params = ', '.join('%s' for i in session['source_institutions'])
    destination_institution_params = ', '.join('%s' for i in session['destination_institutions'])
  except:
    # the session is expired or invalid. Go back to Step 1.
    return render_template('transfers.html', result=Markup('{}'.format(session)))

  # Prepare the query to get the set of rules that match the institutions ans subjects provided.
  source_subject_list = request.form.getlist('source_subject')
  destination_subject_list = request.form.getlist('destination_subject')
  if len(source_subject_list) < 1 or len(destination_subject_list) < 1:
    return(render_template('transfers.html', result=Markup(
                           '<h1 class="error">Missing sending or receiving subject.</h1>')))
  source_subject_params = ', '.join('%s' for s in source_subject_list)
  destination_subject_params = ', '.join('%s' for s in destination_subject_list)
  q = """
  # select
  #         t.source_course_id,
  #         t.destination_course_id,
  #         t.rule_priority,
  #         t.rule_group,
  #         t.min_gpa,
  #         t.max_gpa,
  #         t.transfer_credits,
  #         substring(c1.institution from '[^\d]+') as source_institution,
  #         i1.prompt as source_institution_name,
  #         c1.discipline as source_discipline,
  #         d1.description as source_discipline_name,
  #         c1.catalog_number as source_catalog_number,
  #         c1.credits as source_course_credits,
  #         substring(c2.institution from '[^\d]+') as destination_institution,
  #         i2.prompt as destination_institution_name,
  #         c2.discipline as destination_discipline,
  #         d2.description as destination_discipline_name,
  #         c2.catalog_number as destination_catalog_number,
  #         c2.credits as destination_course_credits,
  #         t.status
  #  from   transfer_rules t,
  #         disciplines d1,
  #         disciplines d2,
  #         courses c1,
  #         courses c2,
  #         institutions i1,
  #         institutions i2
  # where
  #         c1.institution in ({})
  #     and c1.cuny_subject in ({})
  #     and c2.institution in ({})
  #     and c2.cuny_subject in ({})
  #     and c1.course_id = t.source_course_id
  #     and c2.course_id = t.destination_course_id
  #     and i1.code = c1.institution
  #     and i2.code = c2.institution
  #     and d1.discipline = c1.discipline
  #     and d1.institution = c1.institution
  #     and d2.institution = c2.institution
  #     and d2.discipline = c2.discipline
  #   order by lower(i1.prompt), lower(c1.discipline),
  #            to_number(substring(c1.catalog_number from '\d+\.?\d*'), '000000.000'),
  #            lower(i2.prompt)

# I want the list of source courses and the list of destination courses for each rule.
  """.format(source_institution_params,
             source_subject_params,
             destination_institution_params,
             destination_subject_params)
  cursor.execute(q, session['source_institutions'] +
               source_subject_list +
               session['destination_institutions'] +
               destination_subject_list)
  rules = cursor.fetchall()
  if rules == None: rules = []

  cursor.close()
  conn.close()
  # Need to create rule groups, by priority here
  # logger.debug(json.dumps(rules))
  rules_table = extract_groups(rules)

  num_rules = 'are no transfer rules'
  if len(rules) == 1: num_rules = 'is one transfer rule'
  if len(rules) > 1: num_rules = 'are {:,} transfer rules'.format(len(rules))
  result = """
  <h1>Step 3: Review Transfer Rules</h1>
  <fieldset id="rules-fieldset">
    <div>There {} selected.</div>
    <fieldset id="verification-fieldset">
    <p>
      There <span id="num-pending">are no evaluations</span> pending verification.
      <span id="verification-details"><br/>You will need to respond to an email we will send to your
      CUNY email account in order for your evaluations to be recorded.
      </span>
    </p>
    <button type="text" id="send-email" disabled="disabled">
      Review your evaluations before sending a confirmation email to <em id="email-address">{}</em>.
    </button>
  </fieldset>
  <p>Click on a rule to evaluate it.</p>
    <form method="post" action="" id="evaluation-form">
      Please wait for rules to finish loading ...
    </form>
    {}
  </fieldset>
  <a href="/review_transfers/" class="restart">Restart</a>
  """.format(num_rules,
             session['email'],
             rules_table)
  return render_template('transfers.html', result=Markup(result))

# do_form_3()
# -------------------------------------------------------------------------------------------------
def do_form_3(request, session):
  logger.debug('*** do_form_3({})'.format(session))
  evaluations = json.loads(request.form['evaluations'])
  kept_evaluations = [evaluation for evaluation in evaluations if not evaluation['is_omitted']]
  email = session['email']
  if len(kept_evaluations) == 0:
    result = '<h1>There are no evaluations to confirm.</h1>'
  else:
    message_tail = 'evaluation'
    if len(kept_evaluations) > 1:
      count = len(kept_evaluations)
      if count < 13:
        count = ['two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                'eleven', 'twelve'][count - 2]
      message_tail = '{} evaluations'.format(count)
    # Insert these evaluations into the pending_evaluations table.
    conn = pgconnection('dbname=cuny_courses')
    cursor = conn.cursor()
    token = str(uuid.uuid4())
    evaluations = json.dumps(kept_evaluations)
    q = "insert into pending_evaluations (token, email, evaluations) values(%s, %s, %s)"
    cursor.execute(q, (token, email, evaluations))
    conn.commit()
    conn.close()

    # Sentence templates
    evaluation_dict = dict()
    evaluation_dict['ok'] = '{} OK'
    evaluation_dict['not-ok'] = '{} NOT OK: {}'
    evaluation_dict['other'] = 'Other: {}'

    # Send confirmation email
    evaluation_rows = ''
    for evaluation in kept_evaluations:
      event_type = evaluation['event_type']
      if event_type == 'src-ok':
        description = evaluation_dict['ok'].format(evaluation['source_institution'])
      elif event_type == 'dest-ok':
        description = evaluation_dict['ok'].format(evaluation['destination_institution'])
      elif event_type == 'src-not-ok':
        description = evaluation_dict['not-ok'].format(evaluation['source_institution'],
                                                       evaluation['comment_text'])
      elif event_type == 'dest-not-ok':
        description = evaluation_dict['not-ok'].format(evaluation['destination_institution'],
                                                       evaluation['comment_text'])
      else:
        description = evaluation_dict['other'].format(evaluation['comment_text'])

      evaluation_rows += """
        <tr>
          <td style="border: 1px solid black; padding:0.5em;">{}</td>
          <td style="border: 1px solid black; padding:0.5em;">{}</td>
        </tr>
        """.format(evaluation['rule_str'], description)

    hostname = os.environ.get('HOSTNAME')
    if hostname == 'babbage.cs.qc.cuny.edu' or (hostname and hostname.endswith('.local')):
      hostname = 'http://localhost:5000'
    else:
      hostname = 'https://provost-access-148820.appspot.com'
    url = hostname + '/confirmation/' + token

    response = send_token(email, url, evaluation_rows)
    if response.status_code != 202:
      result = 'Error sending email: {}'.format(response.body)
    else:
      result = """
      <h1>Step 4: Respond to Email</h1>
      <p>
        Check your email at {}.<br/>Click on the 'activate these evaluations' button in that email to
        confirm that you actually wish to have your {} recorded.
      </p>
      <p>
        Thank you for your work!
      </p>
      <a href="/review_transfers/" class="restart">Restart</a>

      """.format(email, message_tail)
  return render_template('transfers.html', result=Markup(result))

# PENDING PAGE
# -------------------------------------------------------------------------------------------------
@app.route('/pending')
def pending():
  """ Display pending evaluations.
      TODO: Implement login option so defined users can manage this table.
  """
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  cursor.execute("""
    select email, evaluations, to_char(when_entered, 'Month DD, YYYY HH12:MI am') as when_entered
      from pending_evaluations""")
  rows = ''
  for pending in cursor.fetchall():
    rows += format_pending(pending)
  cursor.close()
  conn.close()

  if rows == '':
    table = '<h2>There are no pending evaluations.</h2>'
  else:
    table = '<table>{}</table>'.format(rows)
  result = """
  <h1>Pending Evaluations</h1>
  {}
  """.format(table)
  return render_template('transfers.html', result=Markup(result))

# format_pending()
# -------------------------------------------------------------------------------------------------
def format_pending(item):
  """ Generate a table row that describes pending evaluations.
  """
  evaluations = json.loads(item['evaluations'])
  suffix = 's'
  if len(evaluations) == 1:
    suffix = ''
  return """<tr><td>{} evaluation{} by {} on {}</td></tr>
  """.format(len(evaluations), suffix, item['email'], item['when_entered'])

# CONFIRMATION PAGE
# -------------------------------------------------------------------------------------------------
# This is the handler for clicks in the confirmation email.
@app.route('/confirmation/<token>', methods=['GET'])
def confirmation(token):
  # Make sure the token is received and is in the pending table.
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  q = 'select * from pending_evaluations where token = %s'
  cursor.execute(q, (token,))
  rows = cursor.fetchall()
  cursor.close()
  conn.close()

  msg = ''
  if len(rows) == 0:
    msg = '<p class="error">This evaluation report has either expired or already been recorded.</p>'
  if len(rows) > 1:
    msg = '<p class="error">Program Error: multiple pending_evaluations.</p>'
  if len(rows) == 1:
    msg = process_pending(rows[0])
  result = """

  <h1>Confirmation</h1>
  <p>Evaluation Report ID: {}</p>
  {}
    """.format(token, msg)
  return render_template('transfers.html', result=Markup(result))


# EVALUATION HISTORY PAGE
# -------------------------------------------------------------------------------------------------
# Display the history of evaluation events for a rule.
#
# DUDE: This is a problem: how do you identify a rule now, and associate a history with it?
# It used to be you could use a pair of course ids, but now the key is (sending_institution,
# sending_discipline, rule_group). So the events table has to be updated to reflect this.
# But where does "the" status for a rule get stored when there are multiple sending and/or
# receiving courses involved? *** TODO ***
# Resolution will come, once the new rule_group table, with its single status, takes over.
#
@app.route('/history/<rule>', methods=['GET'])
def history(rule):
  """ Look up all events for the rule, and report back to the visitor.
  """
  result = rule_history(rule)
  return render_template('transfers.html', result=Markup(result))


# REVIEW_TRANSFERS PAGE
# =================================================================================================
#
@app.route('/review_transfers/', methods=['POST', 'GET'])
def transfers():
  """ (Re-)establish user's mysession and dispatch to appropriate function depending on which form,
      if any, the user submitted.
  """
  logger.debug('*** {} /review_transfers/ ***'.format(request.method))
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

# /_COURSE
# =================================================================================================
# This route is for AJAX access to course catalog information.
@app.route('/_course')
def _course():
  course_id = request.args.get('course_id', 0)
  course = CUNYCourse(course_id)
  note = '<div class="warning"><strong>Note:</strong> Course is not active in CUNYfirst</div>'
  if course.is_active:
    note = ''
  return jsonify({'course_id': course.course_id,
                 'institution': course.institution,
                 'department': course.department,
                 'html': course.html,
                 'note': note})

# /_SESSIONS
# =================================================================================================
# This route is intended as a utility for pruning dead "mysessiob" entries from the db. A periodic
# script can access this url to prevent db bloat when millions of people start using the app. Until
# then, it's just here in case it's needed.
@app.route('/_sessions')
def _sessions():
  conn = pgconnection('dbname=cuny_courses')
  ccursor = conn.cursor()
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

    if num_expired == 1: msg = '<p>Deleted one expired session.</p>'
    else: msg = '<p>Deleted {} expired sessions.</p>'.format(num_expired)
  return result + '</table>' + msg


# COURSES PAGE
# =================================================================================================
# Pick a college, and see catalog descriptions of all courses currently active there.
@app.route('/courses/', methods=['POST', 'GET'])
def courses():
  conn = pgconnection('dbname=cuny_courses')
  cursor = conn.cursor()
  num_courses = 0
  if request.method == 'POST':

    cursor.execute("select * from cuny_subjects")
    cuny_subjects = {row['area']:row['description'] for row in cursor}

    cursor.execute("select * from cuny_careers")
    careers = {(row['institution'], row['career']): row['description'] for row in cursor}

    cursor.execute("select * from designations")
    designations = {row['designation']: row['description'] for row in cursor}

    institution_code = request.form['inst']
    cursor.execute("""
              select name, date_updated
                from institutions
               where code = %s
               """, [institution_code])
    row = cursor.fetchone()
    institution_name = row['name']
    date_updated = row['date_updated'].strftime('%B %d, %Y')
    cursor.execute("""
        select count(*) from courses
         where institution = %s
           and course_status = 'A'
           and can_schedule = 'Y'
           and discipline_status = 'A'
        """, [institution_code])
    num_active_courses = cursor.fetchone()[0]

    result = """
      <h1>{} Courses</h1><p class='subtitle'>{:,} active courses as of {}</p>
      """.format(institution_name, num_active_courses, date_updated)

    query = """
      select * from courses
       where institution = '{}'
         and course_status = 'A'
         and can_schedule = 'Y'
         and discipline_status = 'A'
       order by discipline, number
       """.format(institution_code)
    cursor.execute(query)

    for row in cursor:
      num_courses += 1
      result = result + """
      <p class="catalog-entry"><strong>{} {}: {}</strong> (<em>{}; {}: {}</em>)<br/>
      {:0.1f}hr; {:0.1f}cr; Requisites: <em>{}</em><br/>{} (<em>{}</em>)</p>
      """.format(row['discipline'],
                 row['number'].strip(),
                 row['title'],
                 careers[(row['institution'],row['career'])],
                 row['cuny_subject'], cuny_subjects[row['cuny_subject']],
                 float(row['hours']),
                 float(row['credits']),
                 row['requisites'],
                 row['description'],
                 designations[row['designation']])

  # Form not submitted yet or institution has no courses
  if num_courses == 0:
    prompt = '<fieldset><legend>Select a College</legend>'
    cursor.execute("select * from institutions order by code")
    n = 0
    for row in cursor:
      n += 1
      prompt = prompt + """
      <div class='institution-select'>
        <input type="radio" name="inst" id="inst-{}" value="{}">
        <label for="inst-{}">{}</label>
      </div>
      """.format(n, row['code'], n, row['name'])
    result = """
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


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=5000, debug=True)
