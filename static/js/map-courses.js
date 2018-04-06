$(function ()
{
  //  Initial Settings
  //  =============================================================================================
  $('#need-js').hide();
  $('#transfers-map-div').hide();
  $('form').submit(function (event)
  {
    event.preventDefault();
  });
  var target_course_list = [];
  $('#show-sending, #show-receiving').prop('disabled', true);
  var institutions = [];
  var institutions_request = $.getJSON($SCRIPT_ROOT + '/_institutions');
  institutions_request.done(function (result, status)
                           {
                              institutions = result;
                           });

  //  Event Listeners
  //  =============================================================================================
  /* Change college: update disciplines selection
   */
  $('#institution').change(function ()
  {
    var institution = $('#institution').val();
    if (institution !== 'none')
    {
      var discipline_request = $.getJSON($SCRIPT_ROOT + '/_disciplines',
                                         {institution: institution});
      discipline_request.done(function (discipline_select, text_status)
      {
        $('#discipline').replaceWith(discipline_select);
      });
    }
  });

  /* Clear string of course IDs, update num courses msg, and disable action buttons.
   */
  $('#clear-ids').mouseup(function ()
  {
    $('#course-ids').val('');
    $('#show-sending, #show-receiving').prop('disabled', true);
    $('#num-courses').text('No courses');
    target_course_list = [];
  });

  /* Type of colleges changed. Be sure at least one checkbox is checked.
   */
  $('#bachelors').change(function ()
  {
    if (! $(this).prop('checked'))
    {
      $('#associates').prop('checked', true);
    }
  });
  $('#associates').change(function ()
  {
    if (! $(this).prop('checked'))
    {
      $('#bachelors').prop('checked', true);
    }
  });

  /* Process change in course ID list
   */
  $('#course-ids').change(function ()
  {
    target_course_list = [];
    $('#show-sending, #show-receiving').prop('disabled', true);
    // Parse the course-ids string
    /* Course IDs can be separated by any non-numberic characters.
     * The split() function returns empty strings at beginning and/or end
     * if there are non-numeric chars at beginning or end of the string.
     */
    var course_id_list = $(this).val().split(/\D+/);
    if (course_id_list.length > 0)
    {
      if (course_id_list[course_id_list.length - 1] === '')
      {
        course_id_list.pop();
      }
    }
    if (course_id_list.length > 0)
    {
      if (course_id_list[0] === '')
      {
        course_id_list.shift();
      }
    }
    if (course_id_list.length === 0)
    {
      // No course IDs to look up.
      $('#num-courses').text('No courses');
      return;
    }
    var course_id_request = $.getJSON($SCRIPT_ROOT = '/_courses',
                                      {course_ids: course_id_list.join(':')});
    course_id_request.done(function (result, status)
    {
      switch (result.length)
      {
        case 0:
          // There were courses to look up, but none were found
          $('#num-courses').text('No courses');
          return;
        case 1:
          $('#num-courses').text('One course');
          break;
        default:
          $('#num-courses').text(`${result.length} courses`);
          break;
      }
      //  At least one course was selected: replace target_course_list and enable action buttons
      target_course_list = result;
      $('#show-sending, #show-receiving').prop('disabled', false);
    });
  });

  /* Show Receiving
   */
  $('#show-receiving').mouseup(function ()
  {
    // Header row: sending course and list of receiving colleges
    var colleges = [];
    var associates = $('#associates').prop('checked');
    var bachelors = $('#bachelors').prop('checked');
    for (var i = 0; i < institutions.length; i++)
    {
      if ((institutions[i].bachelors && bachelors) ||
          (institutions[i].associates && associates))
      {
        colleges.push(institutions[i].code);
      }
    }
    var header_row = `<tr>
                        <th rowspan="2">Sending Course</th>
                        <th colspan="${colleges.length}">Receiving College</th></tr>`;
    var colleges_row = '<tr>';
    for (var c = 0; c < colleges.length; c++)
    {
      colleges_row += `<th>${colleges[c].replace('01', '')}</th>` ;
    }
    colleges_row += '</tr>';
    $('#transfers-map-table').html(header_row + colleges_row);
    $('#setup-div').hide();
    $('#transfers-map-div').show();
  });
});
