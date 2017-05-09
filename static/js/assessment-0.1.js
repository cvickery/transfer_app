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
  var sheets = {};
  sheets.documents = {name: 'Documents'};
  sheets.editors = {name: 'Editors'};
  sheets.departments = {name: 'Departments'};
  sheets.plan2org = {name: 'Plan2Org'};
  sheets.known_document_types = {name: 'Known Document Types'};
  sheets.documents_by_type = {name: 'Documents by Type'};
  sheets.documents_by_program = {name: 'Documents by Program'};
  var ranges = [];
  for (var n in sheets)
  {
    if (sheets.hasOwnProperty(n))
    {
      ranges.push(sheets[n].name);
    }
  }

  console.log(ranges);
  manageStatus('Accessing Spreadsheet...', false, true, false);

  gapi.client.sheets.spreadsheets.values.batchGet(
  {
    spreadsheetId: '10QHfEDwmF3N9E1KBnC7XP_DW-Ht51j5UmkRuH-KGbYQ',
    ranges: ranges
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
        user_info += '<p>Your Department: ' + response.result.valueRanges[1].values[row][0] + '</p>';

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
