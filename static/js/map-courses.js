$(function ()
{
  //  Initial Settings
  //  =============================================================================================
  $('#need-js').hide();
  $('#please-wait').hide();
  $('#discipline-span').hide();
  $('#transfers-map-div').hide();
  $('form').submit(function (event)
  {
    event.preventDefault();
  });
  var course_id_list = [];
  $('#show-sending, #show-receiving').prop('disabled', true);
  var institutions = [];
  var institutions_request = $.getJSON($SCRIPT_ROOT + '/_institutions');
  institutions_request.done(function (result, status)
                           {
                              institutions = result;
                           });

//  update_course_count()
//  -----------------------------------------------------------------------------------------------
/*  Utility to show user how many courses have been selected, and to enable course map if that
 *  number is greater than zero.
 */
  function update_course_count()
  {
    $('#show-sending, #show-receiving').prop('disabled', true);
    switch (course_id_list.length)
    {
      case 0:
        // There were courses to look up, but none were found
        $('#num-courses').text('No courses');
        return;
      case 1:
        $('#num-courses').text('One course');
        break;
      default:
        $('#num-courses').text(`${course_id_list.length} courses`);
        break;
    }
    //  At least one course was selected: enable action buttons
    $('#show-sending, #show-receiving').prop('disabled', false);
  }

  //  Event Listeners
  //  =============================================================================================
  /* Any change in Part A, the controls for institution, discipline, and course groups.
   */
  var part_a_change = function ()
  {
    var institution = $('#institution').val();
    var discipline = $('#discipline').val();
    var course_groups = $('#course-groups').val();

    if ($(this).attr('id') === 'institution')
    {
      if (institution === 'none')
      {
        $('#discipline-span').hide();
        return;
      }
      else
      {
        $('#discipline').val('none');
        var discipline_request = $.getJSON($SCRIPT_ROOT + '/_disciplines',
                                           {institution: institution});
        discipline_request.done(function (discipline_select, text_status)
        {
          $('#discipline').replaceWith(discipline_select);
          $('#discipline-span').show();
          $('#discipline').change(part_a_change);
        });
        return;
      }
    }
    if (institution === 'none' || discipline === 'none' || course_groups.length === 0)
    {
      return;
    }
    // Create course_groups_string from the array.
    ranges_str = '';
    for (cg = 0; cg < course_groups.length; cg++)
    {
      switch (course_groups[cg])
      {
        case 'all':
          ranges_str += '0:1000000000;';
          break;
        case 'below':
          ranges_str += '0:100;';
          break;
        case '100':
          ranges_str += '100:200;';
          break;
        case '200':
          ranges_str += '200:300;';
          break;
        case '300':
          ranges_str += '300:400;';
          break;
        case '400':
          ranges_str += '400:500;';
          break;
        case '500':
          ranges_str += '500:600;';
          break;
        case '600':
          ranges_str += '600:700;';
          break;
        case 'above':
          ranges_str += '700:1000000000;';
          break;
      }
    }
    // Trim trailing semicolor
    ranges_str = ranges_str.substring(0, ranges_str.length - 1);
    var find_course_ids_request = $.getJSON($SCRIPT_ROOT + '/_find_course_ids',
                                           {
                                              institution: institution,
                                              discipline: discipline,
                                              ranges_str: ranges_str
                                           });
    find_course_ids_request.done(function (result, status)
    {
      course_id_list = [];
      for (var i = 0; i < result.length; i++)
      {
        course_id_list.push(result[i][0]);
      }
      update_course_count();
    });
  };

  /* Clear string of course IDs, update num courses msg, and disable action buttons.
   */
  $('#clear-ids').mouseup(function ()
  {
    $('#course-ids').val('');
    $('#show-sending, #show-receiving').prop('disabled', true);
    $('#num-courses').text('No courses');
    course_id_list = [];
  });

  /* Type of colleges changed. Be sure at least one checkbox is checked.
   */
  $('#bachelors').change(function ()
  {
    if (!$(this).prop('checked'))
    {
      $('#associates').prop('checked', true);
    }
  });

  $('#associates').change(function ()
  {
    if (!$(this).prop('checked'))
    {
      $('#bachelors').prop('checked', true);
    }
  });

  $('#institution, #course-groups').change(part_a_change);

  /* Any change in Part B, the Course ID list
   */
  $('#course-ids').change(function ()
  {
    course_id_list = [];
    $('#show-sending, #show-receiving').prop('disabled', true);
    // Parse the course-ids string
    /* Course IDs can be separated by any non-numberic characters.
     * The split() function returns empty strings at beginning and/or end if there are separator
     * chars at beginning or end of the string, so they have to be trimmed away.
     */
    course_id_list = $(this).val().split(/\D+/);
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
    update_course_count();
  });

  /* Show Setup
   */
  $('#show-setup').mouseup(function ()
  {
    $('#setup-div').show();
    $('#transfers-map-div').hide();
  });

  /*  Show Receiving and Show Sending event handlers
   *  ---------------------------------------------------------------------------------------------
   */
  $('#show-receiving, #show-sending').mouseup(function ()
  {
    var request_type = $(this).attr('id');

    // Header row: "Sending" or "Receiving" Course and list of receiving colleges
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
    if (request_type === 'show-sending')
    {
      header_row = `<tr>
                      <th colspan="${colleges.length}">Sending College</th>
                      <th rowspan="2">Receiving Course</th></tr>`;
    }
    var colleges_row = '<tr>';
    for (var c = 0; c < colleges.length; c++)
    {
      colleges_row += `<th>${colleges[c].replace('01', '')}</th>` ;
    }
    colleges_row += '</tr>';
    // Get the table body rows from /_map_courses
    $('#please-wait').show();
    var map_request = $.getJSON($SCRIPT_ROOT = '/_map_course',
                                        {
                                          course_id_list: JSON.stringify(course_id_list),
                                          colleges: JSON.stringify(colleges),
                                          request_type: $(this).attr('id')
                                        });
    map_request.done(function (result, status)
    {
      $('#please-wait').hide();
      $('#transfers-map-table').html(header_row + colleges_row + result);
      $('#setup-div').hide();
      $('#transfers-map-div').show();
    });
  });
});
