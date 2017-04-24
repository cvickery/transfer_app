// var auth2; // The Sign-In object.
// var googleUser; // The current user.
// console.log('login.js here');
// /**
//  * Calls startAuth after Sign in V2 finishes setting up.
//  */
// var appStart = function ()
// {
//   console.log('appStart here');
//   gapi.load('auth2', initSigninV2);
// };

// /**
//  * Initializes Signin v2 and sets up listeners.
//  */
// var initSigninV2 = function ()
// {
//   auth2 = gapi.auth2.init({
//       client_id: '4735595349-oje44rn7t2ohu3881ocpf2u7g6gt61c6.apps.googleusercontent.com',
//       scope: 'profile'
//   });

//   // Listen for sign-in state changes.
//   auth2.isSignedIn.listen(signinChanged);

//   // Listen for changes to current user.
//   auth2.currentUser.listen(userChanged);

//   // Sign in the user if they are currently signed in.
//   if (auth2.isSignedIn.get() == true)
//   {
//     auth2.signIn();
//   }

//   // Start with the current live values.
//   refreshValues();
// };

// /**
//  * Listener method for sign-out live value.
//  *
//  * @param {boolean} val the updated signed out state.
//  */
// var signinChanged = function (val)
// {
//   console.log('Signin state changed to ', val);
//   document.getElementById('signed-in-cell').innerText = val;
// };

// /**
//  * Listener method for when the user changes.
//  *
//  * @param {GoogleUser} user the updated user.
//  */
// var userChanged = function (user)
// {
//   console.log('User now: ', user);
//   googleUser = user;
//   updateGoogleUser();
//   document.getElementById('curr-user-cell').innerText =
//     JSON.stringify(user, undefined, 2);
// };

// /**
//  * Updates the properties in the Google User table using the current user.
//  */
// var updateGoogleUser = function ()
// {
//   console.log('updateGoogleUser here');
//   if (googleUser)
//   {
//     document.getElementById('user-id').innerText = googleUser.getId();
//     document.getElementById('user-scopes').innerText =
//       googleUser.getGrantedScopes();
//     document.getElementById('auth-response').innerText =
//       JSON.stringify(googleUser.getAuthResponse(), undefined, 2);
//   }
//   else
//   {
//     document.getElementById('user-id').innerText = '--';
//     document.getElementById('user-scopes').innerText = '--';
//     document.getElementById('auth-response').innerText = '--';
//   }
// };

// /**
//  * Retrieves the current user and signed in states from the GoogleAuth
//  * object.
//  */
// var refreshValues = function ()
// {
//   if (auth2)
//   {
//     console.log('refreshValues here');

//     googleUser = auth2.currentUser.get();

//     document.getElementById('curr-user-cell').innerText =
//       JSON.stringify(googleUser, undefined, 2);
//     document.getElementById('signed-in-cell').innerText =
//       auth2.isSignedIn.get();

//     updateGoogleUser();
//   }
// };

var auth = null;
console.log('prototype.js here');
function appStart()
{
  console.log('doit here');

  gapi.load('auth2', function ()
  {
    auth = gapi.auth2.init(
    {
      client_id: '4735595349-oje44rn7t2ohu3881ocpf2u7g6gt61c6.apps.googleusercontent.com',
      scope: 'profile'
    });
    console.log(auth);
    auth.then(authInit, authError);
  });
}

function authInit()
{
  console.log('authInit here');
  var auth = gapi.auth2.getAuthInstance();
  if (auth.isSignedIn.get())
  {
    console.log('is signed in');
    console.log(auth);
    onSignIn(auth.currentUser.get());
  }
  else
  {
    console.log('signing in');
    auth.signIn({scope: 'profile email openid', prompt: 'select_account'}).then(signInListener);
  }
}

function authError(reason)
{
  console.log('authError', reason);
  if (reason.error.indexOf('idpiframe_initialization_failed') !== -1)
  {
    document.getElementById('error-msg').innerText = 'You need to enable cookies from Google ' +
                                                     'to use this site.';
  }
}

function signInListener(isSignedIn)
{
  console.log('signInListener: ' + isSignedIn);
}
function onSignIn(user)
{
  var profile = user.getBasicProfile();
  $('#user-name').text(profile.getName());
  console.log(profile.getName());
}
