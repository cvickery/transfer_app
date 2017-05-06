var auth = null;
console.log('login.js here');

//  manageStatus()
//  -------------------------------------------------------------------
/*  Manage the login status area, which has room for a text message, a signin
 *  button, a signout button, and a switch accounts button. If all four are null/false,
 *  the whole thing goes away.
 */
function manageStatus(msg = null, show_signin = false, show_signout = false, show_switch = false)
{
  console.log('manageStatus:', msg, show_signin, show_signout, show_switch);
  if (!msg && !show_signin && !show_signout && !show_switch)
  {
    $('#login-status-div').hide();
    return;
  }
  var buttons = '';
  document.getElementById('error-msg').innerText = msg ? msg : '';
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
                                                      '/favicon.ico"> '
      document.getElementById('user-name').innerText = 'Stranger';
      manageStatus('', true, false, false);
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
//  -------------------------------------------------------------------
function appStart()
{
  console.log('appStart here');
  // document.getElementById('error-msg').innerText = '';
  manageStatus();
  try
  {
    gapi.load('client:auth2', function ()
    {
      auth = gapi.auth2.init(
      {
        client_id: '4735595349-oje44rn7t2ohu3881ocpf2u7g6gt61c6.apps.googleusercontent.com',
        scope: 'profile'
      });
      auth.then(authInit, authError);
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
      auth.signIn({scope: 'profile email openid', prompt: 'select_account'})
           .then(signInListener, authError);
      manageStatus('Be sure pop-ups from Google are allowed for this site.', true, false, false);
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
    onSignIn(userObj)
  }
  else
  {
    console.log('User not signed in');
    manageStatus('Program error: “not signed in ”' + reason.error);
  }
}

//  authError()
//  -------------------------------------------------------------------
function authError(reason)
{
  console.log('authError reason:', reason);
  var msg = 'Signin Failed';
  if ((typeof reason.error) !== "undefined")
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
      manageStatus('Be sure pop-ups from Google are allowed for this site.', true, false, false);
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
                                                  profile.getImageUrl() + '"> '
  document.getElementById('user-name').innerText = profile.getName();
  var email = profile.getEmail();
  var email_domain = email.substr(email.indexOf('@')).toLowerCase();
  console.log('onSignIn email & domain:', email, email_domain);
  if (email_domain !== '@qc.cuny.edu')
  {
    document.getElementById('error-msg').innerText = 'You are signed in as ' + email +
        ', but you must be signed in using a QC email address to access this site.'
    manageStatus('You are signed in as ' + email +
        ', but you must be signed in using a QC email address to use this site.', false, true, true);
  }
  else
  {
    // document.getElementById('error-msg').innerText = 'Everything is hunky-dory.';
    manageStatus('', false, true, false);
    gapi.client.init(
    {
      apiKey: 'AIzaSyCqVYaYohqgP_b4DekcHKZAPIHiCIYl3r0',
      clientId: '4735595349-oje44rn7t2ohu3881ocpf2u7g6gt61c6.apps.googleusercontent.com',
      scope: 'profile',
    }).then(clientReady);
    $('#content-div').show();
  }
}
