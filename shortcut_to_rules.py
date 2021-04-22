#! /usr/local/bin/python3
""" Generate list of rules to evaluate without need to do so much navigation/selection.
"""

from collections import namedtuple

from app_header import header
from top_menu import top_menu
from pgconnection import PgConnection

"""
    The idea is to skip the "select disciplines" form by knowing the reviewer's email.
    They still have to pick the other college(s) involved
    Get email; look up their college, department, and name
      If not in person_roles table, send them to longcut form
      If associate's college, assume sending rules
      If bachelor's college, assume receiving rules
      If both, ask which way
      (Multi?)select college(s) of interest
      Limit to BKCR?
      Include MESG?

    Heuristic: Look at rules where the sending/receiving course is person's discipline instead of
    searching by cuny_subject.
    Heuristic: Look at rules for courses most-frequently transferred.
"""
Role = namedtuple('Role', 'role institution organization')


def shortcut_to_rules(request, session):
  """ Given a user's email address, see if they are in the person_roles table, and if so generate
      a quick list of rule keys based on some simple additional info.
  """
  for key in session.keys():
    print(f'{key}: {session[key]}')
  print(f'{request.form.get("remember_me")=}')

  # session.clear()

  conn = PgConnection()
  cursor = conn.cursor()

  # Determine user
  email = None
  email_prompt = 'Your CUNY email address'
  old_value = ''
  while email is None:
    if 'email' in request.form:
      # Request Form overrides session
      email = request.form.get('email')
      if email.lower().endswith('@cuny.edu') or email.lower().endswith('.cuny.edu'):
        session['email'] = request.form.get('email')
        session['remember_me'] = request.form.get('remember_me') == 'on'
        session.permanent = session['remember_me']
      else:
        old_value = email
        email = None
        email_prompt = 'CUNY email addresses end with “cuny.edu”'

    elif 'email' in session:
      email = session['email']

    else:
      old_value = ''
      email = None
      email_prompt = 'Your CUNY email address'

    if email:
      cursor.execute(f"""
      select name, email from people where email ~* %s or alternate_emails ~* %s
      """, (email, email))
      if cursor.rowcount == 1:
        row = cursor.fetchone()
        name, email = row.name, row.email
        # Get roles
        cursor.execute(f"""
        select role, institution, organization from person_roles where email ~ %s
        """, (email, ))
        if cursor.rowcount == 0:
          old_value = email
          email = None
          email_prompt = (f'No roles available for your email address. Change, or '
                          '<a href="/review_rules/">Use This Link</a>')
        else:
          roles = [Role(row.role, row.institution, row.organization) for row in cursor.fetchall()]
          print(f'{roles=}')
      elif cursor.rowcount == 0:
        # Not a known person
        old_value = email
        email = None
        email_prompt = ''
      else:
        # Ambiguous Email
        email = None
        email_prompt = 'Fix Ambiguous Email Address'

    if email is None:
      # Get user’s (fixed) email and come back here with it.
      email_form = f"""
        <h1>Your CUNY email address, please.</h1>
        <fieldset><legend>{email_prompt}</legend>
          <form method='POST', action='/quick_rules/'>
            <label for="email">Email</label> <input type="text"
                                                    id="email"
                                                    name="email"
                                                    value="{old_value}"
                                                    size="30"/>
            <button type="submit">Submit</button><br>
            <label for="remember-me">Remember Me</label> <input type="checkbox"
                                                                name="remember_me"
                                                                value="{remember_me}"
                                                                id="remember-me"/>
          </form>
        </fieldset
    """
      conn.close()
      return email_form

  roles_str = '<br>'.join([f'{r.role} ({r.institution}:{r.organization})' for r in roles])
  debug = f'<h2>{name}</h2>{roles_str}'

  # Got email, name, and non-empty list of roles. Get search parameters

  result = f"""
  {header(title='Review Rules: Review Selected Rules',
          nav_items=[{'type': 'link',
          'href': '/',
          'text': 'Main Menu'},
          {'type': 'link',
           'href': '/review_rules',
           'text': 'Change Colleges'},
           {'type': 'button',
            'class': 'back-button',
            'text': 'Change Subjects'

           }])}
    <details open>
      <summary>Instructions (click to open/close)</summary>
      <hr>
      <p>
        There will be instructions
      </p>
      </details>
    <p>{debug}</p>
"""

  return result

  # Generate list of rule_keys
  if len(selected_rules) == 0:
    num_rules = 'No matching transfer rules found.'
  if len(selected_rules) == 1:
    num_rules = 'There is one matching transfer rule.'
  if len(selected_rules) > 1:
    num_rules = f'There are {len(selected_rules):,} matching transfer rules.'

  rules_table = format_rules(selected_rules, scrollable=True)

  result = f"""
  {header(title='Review Rules: Review Selected Rules',
          nav_items=[{'type': 'link',
          'href': '/',
          'text': 'Main Menu'},
          {'type': 'link',
           'href': '/review_rules',
           'text': 'Change Colleges'},
           {'type': 'button',
            'class': 'back-button',
            'text': 'Change Subjects'

           }])}
    <details open>
      <summary>Instructions (click to open/close)</summary>
      <hr>
      {num_rules}
      <p>
      Blanket Credit courses are <span class="blanket">highlighted like this</span>.
      </p>
      <p>
        Rules that are <span class="credit-mismatch">highlighted like this</span> have a different
        number of credits taken from the number of credits transferred.
        Hover over the “=>” to see the numbers of credits.
      </p>
      <p>
        Credits in parentheses give the number of credits transferred where that does not match the
        nominal number of credits for a course.
      </p>
      <p>
        Rules that are <span class="evaluated">highlighted like this</span> are ones that you have
        reviewed but not yet submitted.
      </p>
      <p class="call-to-action">
        Click on a rule to review it
      </p>
    </details>
    <fieldset id="verification-fieldset"><legend>Review Reviews</legend>
        <p id="num-pending">You have not reviewed any transfer rules yet.</p>
        <button type="text" id="send-email" disabled="disabled">
        Review Your Reviews
      </button>
      <form method="post" action="#" id="review-form">
        Waiting for rules to finish loading ...
      </form>
    </fieldset>
    <div id="rules-table-div" class="selection-table-div table-height">
    {rules_table}
    </div>
  """
  return render_template('review_rules.html', result=Markup(result))
