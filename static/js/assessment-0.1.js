// assessment.js
/*
 * Try to access the assessment repository spreadsheet and look up the user's access rights to it.
 */
console.log('assessment.js here');
$(function ()
{
 $('#content-div').html('<h1>Assessment Repository</h1><div id="repository-info"></div>').show();
});

function clientReady(email)
{
  console.log('clientReady', gapi.client);
  console.log('get the values', gapi.client.sheets.spreadsheets.values);
  var user = email.substr(0, email.indexOf('@'));
  manageStatus('Accessing Spreadsheet...', false, true, false);
  gapi.client.sheets.spreadsheets.values.batchGet(
  {
    spreadsheetId: '10QHfEDwmF3N9E1KBnC7XP_DW-Ht51j5UmkRuH-KGbYQ',
    ranges: ['Documents', 'Editors']
  }).then(function (response)
  {
    // values.get success
    console.log(response.result);
    manageStatus('', false, true, false);
    // Tell what kind of person this is, and how many docs there are
    var user_info = '';
    for (var row = 1; row < response.result.valueRanges[1].values.length; row++)
    {
      if (response.result.valueRanges[1].values[row][1] === user)
      {
        user_info += '<p>Department: ' + response.result.valueRanges[1].values[row][0] + '</p>';
      }
    }
    if (user_info === '')
    {
      user_info = '<p>You have not been authorized to access the assessment repository.</p>'
    }
    $('#repository-info').html(user_info);
  }, function (reason)
  {
    // values.get fail
    console.log('values.get Error: ' + reason.result.error.message);
  });
}
