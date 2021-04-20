#! /usr/local/bin/python3
""" Generate list of rules to evaluate without need to do so much navigation/selection.
"""
from app_header import header
from top_menu import top_menu

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
"""


def shortcut_to_rules(request, session):
  """ Given a user's email address, see if they are in the person_roles table, and if so generate
      a quick list of rule keys based on some simple additional info.
  """
  print(f'{session.keys()=}')
  print(f'{request.form=}')

  # Determine user, other college(s) of interest, and parameters (if_bkcr, if_mesg). Known values
  # from session pre-populate the form.
  if 'email' in request.form:
    email = request.form.get('email')
    session['email'] = request.form.get('email')
    session['remember_me'] = request.form.get('remember-me') == 'on'
    session.permanent = session['remember_me']

  elif 'email' in session:
    email = session['email']

  else:
    email = None

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
