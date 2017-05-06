// assessment.js
/*
 * Try to access the assessment repository spreadsheet and look up the user's access rights to it.
 */
console.log('assessment.js here');
$(function ()
{
 $('#content-div').html('<h1>Assessment Repository Stuff</h1>').show();
});

function clientReady()
{
  console.log('clientReady', gapi.client);
  /*******************************************************************************************
   *  TODO: this stuff was supposed to be done when you called gapi.client.init in login.js  *
   *******************************************************************************************/
  var DISCOVERY_DOCS = ['https://sheets.googleapis.com/$discovery/rest?version=v4'];
  var SCOPES = 'HTTPS://www.googleapis.com/auth/spreadsheets.readonly';

  gapi.client.init(
  {
    discoveryDocs: DISCOVERY_DOCS,
    clientId: '4735595349-oje44rn7t2ohu3881ocpf2u7g6gt61c6.apps.googleusercontent.com',
    scope: SCOPES
  }).then(function ()
  {
    // client.init success
    console.log('get the values');
    gapi.client.sheets.spreadsheets.values.get(
    {
      spreadsheetId: '10QHfEDwmF3N9E1KBnC7XP_DW-Ht51j5UmkRuH-KGbYQ',
      range: 'Documents'
    }).then(function (response)
    {
      // values.get success
      console.log(response.result);
    }, function (reason)
    {
      // values.get fail
      console.log('Error: ' + reason.result.error.message);
    });
  }, function (reason)
  {
    // client.init fail
    console.log('Error: ' + reason.result.error.message);
  });
}
