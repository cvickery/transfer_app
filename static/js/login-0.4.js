console.log('login.js here');
var signin_msg =
    '<ul><li>You need to sign into Google using your QC account in order to use this site.</li>' +
    '<li>Be sure your browser is not set to block pop-ups or third-party cookies from ' +
    'Google before signing in.</li>' +
    '<li>When prompted for your email address, use the short form (jdoe@qc.cuny.edu ' +
    'rather than jane.doe@qc.cuny.edu). Students: use your CAMS account address.</li></ul>' +
    '<p>See <a target="_blank" href="http://ctl.qc.cuny.edu/google">http://ctl.qc.cuny.edu/google' +
    '</a> for more information.</p>';
var auth = null;
var client = null;

//  manageStatus()
//  -------------------------------------------------------------------
/*  Manage the login status area, which has room for a text message, a signin
 *  button, a signout button, and a switch accounts button. If all four are null/false,
 *  the whole thing goes away.
 */
function manageStatus(msg, show_signin, show_signout, show_switch)
{
  if (msg === undefined)
  {
    msg = '';
  }
  if (show_signin === undefined)
  {
    show_signin = false;
  }
  if (show_signout === undefined)
  {
    show_signout = false;
  }
  if (show_switch === undefined)
  {
    show_switch = false;
  }
  console.log('manageStatus:', msg, show_signin, show_signout, show_switch);
  if (msg === '' && !show_signin && !show_signout && !show_switch)
  {
    $('#login-status-div').hide();
    return;
  }
  var buttons = '';
  document.getElementById('error-msg').innerHTML = msg ? msg : '';
  if (show_signin)
  {
    buttons += '<button id="signin-button">Sign In</button>';
  }
  if (show_signout)
  {
    buttons += '<button id="signout-button">Sign Out</button>';
  }
  if (show_switch)
  {
    buttons += '<button id="switch-button">Switch User</button>';
  }

  document.getElementById('signin-controls').innerHTML = buttons;
  $('#login-status-div').show();

  //  Signin handler
  $('#signin-button').click(function ()
  {
    console.log('signin click');
    $('#content-div').hide();
    gapi.auth2.getAuthInstance()
              .signIn({scope: 'profile email openid', prompt: 'select_account'})
              .then(signInListener, authError);
  });

  //  Signout handler
  $('#signout-button').click(function ()
  {
    console.log('signout click');
    $('#content-div').hide();
    auth = gapi.auth2.getAuthInstance();
    auth.signOut().then(function ()
    {
      document.getElementById('user-img').innerHTML = '<img alt="" width="32" src="' +
                                                      '/favicon.ico"> ';
      document.getElementById('user-name').innerText = 'Stranger';
      manageStatus(signin_msg, true, false, false);
    });
  });

  //  Switch user handler
  $('#switch-button').click(function ()
  {
    console.log('switch click');
    $('#content-div').hide();
    gapi.auth2.getAuthInstance()
               .signIn({scope: 'profile email openid', prompt: 'select_account'})
               .then(signInListener, authError);
  });
}

//  appStart()
//  ---------------------------------------------------------------------------
/*  Initialize Client API and manage User signin.
 *
 */
function appStart()
{
  console.log('appStart here');
  console.log(document.getElementById('need-js'));
  document.getElementById('need-js').setAttribute('data-app-started', true);
  console.log(document.getElementById('need-js'));
  manageStatus('Application Initializing...');
  try
  {
    gapi.load('client:auth2', function ()
    {
      console.log('client.init');
      gapi.client.init(
      {
        discoveryDocs: ['https://sheets.googleapis.com/$discovery/rest?version=v4'],
        clientId: '4735595349-oje44rn7t2ohu3881ocpf2u7g6gt61c6.apps.googleusercontent.com',
        scope: 'https://www.googleapis.com/auth/spreadsheets.readonly'
      }).then(authInit);
    });
  }
  catch (e)
  {
    manageStatus('appStart: ' + e);
  }
}

//  authInit()
//  -------------------------------------------------------------------
function authInit()
{
  console.log('authInit here');
  try
  {
    var auth = gapi.auth2.getAuthInstance();
    if (auth.isSignedIn.get())
    {
      console.log('authInit is signed in:', auth);
      onSignIn(auth.currentUser.get());
    }
    else
    {
      console.log('authInit signing in');
      auth.signIn(
      {
        scope: 'profile email openid',
        prompt: 'select_account'
      }).then(signInListener, authError);
      manageStatus(signin_msg, true, false, false);
    }
  }
  catch (e)
  {
    // document.getElementById('error-msg').innerText = 'authInit error: ' + e;
    manageStatus('authInit error: ' + e);
  }
}

//  signInListener()
//  -------------------------------------------------------------------
function signInListener(userObj)
{
  console.log('signInListener: ', userObj);
  if (userObj.isSignedIn())
  {
    onSignIn(userObj);
    manageStatus('You are signed in.', false, true, false);
  }
  else
  {
    console.log('User not signed in');
    manageStatus('Program error: “Useer not signed in”', true, false, false);
  }
}

//  authError()
//  -------------------------------------------------------------------
function authError(reason)
{
  console.log('authError reason:', reason);
  var msg = 'Signin Failed';
  if ((typeof reason.error) !== undefined)
  {
    console.log((typeof reason.error) !== undefined);
    if (reason.error.indexOf('idpiframe_initialization_failed') !== -1)
    {
      msg += ': Your browser is not set to allow third-party cookies from Google.';
    }
    if (reason.error.indexOf('popup_closed_by_user') !== -1)
    {
      msg += ': You canceled the signin dialog.';
    }
    if (reason.error.indexOf('access_denied') !== -1)
    {
      msg += ': You did not grant the access rights this site needs.';
    }
    manageStatus(msg, true, false, false);
  }
  else
  {
      manageStatus(signin_msg, true, false, false);
  }
}

//  onSignIn()
//  -------------------------------------------------------------------
function onSignIn(userObj)
{
  console.log('onSignIn userObj: ', userObj);
  console.log('onSignIn scopes: ', userObj.getGrantedScopes());
  console.log('onSignIn domains: ', userObj.getHostedDomain());
  var profile = userObj.getBasicProfile();
  console.log('onSignIn profile: ', profile);
  // document.getElementById('error-msg').innerText = '';
  document.getElementById('user-img').innerHTML = '<img alt="" width="32" src="' +
                                                  profile.getImageUrl() + '"> ';
  document.getElementById('user-name').innerText = profile.getName();
  var email = profile.getEmail();
  var email_domain = email.substr(email.indexOf('@')).toLowerCase();
  console.log('onSignIn email & domain:', email, email_domain);
  if (email_domain !== '@qc.cuny.edu')
  {
    manageStatus('You are signed in to Google as ' + email + '.<br/>' + signin_msg,
                 false, true, true);
  }
  else
  {
    // User is authenticated
    manageStatus('', false, true, false);

    // Initialize client APIs if there is a clientReady function available
    if (typeof clientReady === 'function')
    {
      clientReady(email);
    }
    else
    {
      console.log('no clientReady');
    }
    $('#content-div').show();
  }
}
