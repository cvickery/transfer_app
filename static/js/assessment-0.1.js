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
  var start_query = Date.now();
  gapi.client.sheets.spreadsheets.values.batchGet(
  {
//    spreadsheetId: '10QHfEDwmF3N9E1KBnC7XP_DW-Ht51j5UmkRuH-KGbYQ',
    spreadsheetId: '11PpZD8sYteMRez-5PJHybBish0OA5VKWyJmnXyXDHpk',
    ranges: ranges
  }).then(function (response)
  {
    // values.get success
    console.log(response.result);
    var elapsed = (Date.now() - start_query) / 1000;
    manageStatus('Sheet access took ' + Number(elapsed).toLocaleString() + ' seconds', false, true, false);
    // For each sheet in the result set, augment it with its data array and cols structure
    // [Assumes the returned valueRanges array matches the order
    // of the ranges array passed to batchGet().]
    for (var i = 0; i < ranges.length; i++)
    {
      // sanity check
      if (ranges[i] !==
          response.result.valueRanges[i].range.replace(/'/g, '').substr(0, ranges[i].length))
      {
        throw new Error('Workbook sheet order: ' + ranges[i] + ' !== ' +
                          response.result.valueRanges[i].range.substr(0, ranges[i].length));
      }

      // Set up sheet info object
      var sheet = ranges[i].replace(/'/g, '').toLowerCase().replace(/ /g, '_');
      sheets[sheet].values = response.result.valueRanges[i].values;
      var cols = {};
      for (var j = 0; j < sheets[sheet].values[0].length; j++)
      {
        cols[sheets[sheet].values[0][j].replace(/'/g, '').toLowerCase().replace(/ /g, '_')] = j;
      }
      sheets[sheet].cols = cols;
    }

    console.log('Sheets: ', sheets);

    // Summarize the repository state
    var state_info = '<div><h2>Repository Summary</h2><table><tr><th>Dept</th><th>Docs</th>' +
                     '<th>By Type</th><th>By Program</th></tr>';
    var docs_by_dept = {};
    var depts = [];
    var total_docs = 0, total_by_type = 0, total_by_prog = 0;
    for (var d_row = 1; d_row < sheets.documents.values.length; d_row++)
    {
      var dept = sheets.documents.values[d_row][sheets.documents.cols.department];
      var doc_id = sheets.documents.values[d_row][sheets.documents.cols.document_id];
      if (!docs_by_dept[dept])
      {
        depts.push(dept);
        docs_by_dept[dept] =
        {
          num_docs: 0,
          num_by_type: 0,
          num_by_prog: 0
        };
      }
      docs_by_dept[dept].num_docs++;
      total_docs++;
      for (var t_row = 1; t_row < sheets.documents_by_type.values.length; t_row++)
      {
        if (doc_id ===
            sheets.documents_by_type.values[t_row][sheets.documents_by_type.cols.document_id])
        {
          docs_by_dept[dept].num_by_type++;
          total_by_type++;
          break; // count each doc just once
        }
      }
      for (var p_row = 1; p_row < sheets.documents_by_program.values.length; p_row++)
      {
        if (doc_id ===
            sheets.documents_by_program.values[p_row][sheets.documents_by_program.cols.document_id])
        {
          docs_by_dept[dept].num_by_prog++;
          total_by_prog++;
          break; // count each doc just once
        }
      }
    }
    console.log(docs_by_dept);
    // Sort in decreasing order by number of documents
    depts.sort(function (a, b)
    {
      if (docs_by_dept[a].num_docs > docs_by_dept[b].num_docs)
      {
        return -1;
      }
      if (docs_by_dept[a].num_docs < docs_by_dept[b].num_docs)
      {
        return +1;
      }
      else
      {
        return 0;
      }
    });

    for (var dept in depts)
    {
      state_info += '<tr><td>' + depts[dept] + '</td><td>' + docs_by_dept[depts[dept]].num_docs + '</td>' +
      '<td>' + docs_by_dept[depts[dept]].num_by_type + '</td>' +
      '<td>' + docs_by_dept[depts[dept]].num_by_prog + '</td></tr>';
    }

    state_info += '<tr><td>Total</td><td>' + total_docs + '</td><td>' + total_by_type +
                  '</td><td>' + total_by_prog + '</td></tr>';
    state_info += '</table></div>';

    // Tell what kind of person this is, and how many docs there are
    var user_info = '<div><h2>Your Editing Information</h2><div>';
    var user_found = false;
    for (var row = 1; row < sheets.editors.values.length; row++)
    {
      if (sheets.editors.values[row][sheets.editors.cols.user] === user)
      {
        user_found = true;
        user_info += '<p><strong>Department:</strong> ' +
          sheets.editors.values[row][sheets.editors.cols.department] + '</p>';
        user_info += '<p><strong>Can access all departments:</strong> ' +
          (sheets.editors.values[row][sheets.editors.cols.is_super] ? 'Yes' : 'No') + '</p>';
        user_info += '<p><strong>View-only access:</strong> ' +
          (sheets.editors.values[row][sheets.editors.cols.can_edit] ? 'Yes': 'No') + '</p>';
        if (sheets.editors.values[row][sheets.editors.cols.events])
        {
          user_info += '<p><strong>Edit history:</strong> ' +
            Number(sheets.editors.values[row][sheets.editors.cols.events]).toLocaleString() +
            ' actions</p>';
        }
      }
    }
    if (!user_found)
    {
      user_info += '<p>You have not been authorized to access the assessment repository.</p>';
    }
    user_info += '</div></div>';

    $('#repository-info').html(state_info + user_info);
  }, function (reason)
  {
    // values.get fail
    console.log('values.get Error: ' + reason.result.error.message);
  });
}
