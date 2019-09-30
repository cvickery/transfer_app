import ScrollableTable from '/static/js/scrollable_tables.js';

$(function ()
{
  //  Initial Settings
  //  =============================================================================================
  $('#loading, #discipline-span, #transfers-map-div, #pop-up-div').hide();
  $('#show-sending, #show-receiving').prop('disabled', true);
  let pop_up_content = 'None';
  $('form').submit(function (event)
  {
    event.preventDefault();
  });

  // Global action: escape key hides pop-ups; question key shows instructions.
  $('*').keyup(function (event)
  {
    if (event.keyCode === 27)
    {
      $('#pop-up-div').hide();
    }
    else if (event.key === '?')
    {
      $('.instructions').show();
    }
    else if (event.keyCode === 37 && !($('#pop-up-div').is(':hidden')))
    {
      // backarrow in pop-up
      $('#pop-up-content').html(pop_up_content);
    }
  });

  // Clicking on the dismiss bar also hides the pop-ups.
  $('#dismiss-bar').click(function ()
  {
    $('#pop-up-div').hide();
  });



  //  Globals
  //  ===============================================================================================
  let course_list = [];
  let institutions = [];
  const institutions_request = $.getJSON($SCRIPT_ROOT + '/_institutions');
  institutions_request.done(function (result, status)
  {
    if (status !== 'success')
    {
      alert(status);
    }
    else
    {
      institutions = result;
    }
  });

  //  update_course_count()
  // -----------------------------------------------------------------------------------------------
  /*  Utility to show user how many courses have been selected, and to enable course map activators if
   *  that number is greater than zero.
   */
  function update_course_count()
  {
    $('#show-sending, #show-receiving').prop('disabled', true);
    switch (course_list.length)
    {
    case 0:
      // There were courses to look up, but none were found
      $('#num-courses').text('No courses selected yet.');
      $('#num-courses').css('color', '#a00');
      return;
    case 1:
      $('#num-courses').text('One course selected.');
      $('#num-courses').css('color', '#472');
      break;
    default:
      $('#num-courses').text(`${course_list.length} courses selected.`);
      $('#num-courses').css('color', '#472');
      break;
    }
    //  At least one course was selected: enable action buttons
    $('#show-sending, #show-receiving').prop('disabled', false);
  }

  //  Event Listeners
  //  =============================================================================================
  /* Any change in the controls for institution, discipline, and course groups.
   */
  const part_a_change = function ()
  {
    const institution = $('#institution').val();
    const discipline = $('#discipline').val();
    const course_groups = $('#course-groups').val();

    if ($(this).attr('id') === 'institution')
    {
      course_list = [];
      update_course_count();
      if (institution === 'none')
      {
        $('#discipline-span').hide();
      }
      else
      {
        const discipline_request = $.getJSON($SCRIPT_ROOT + '/_disciplines',
          {institution: institution});
        discipline_request.done(function (discipline_select, status)
        {
          if (status !== 'success')
          {
            alert(status);
          }
          else
          {
            $('#discipline').replaceWith(discipline_select);
            $('#discipline').val('none');
            $('#discipline').change(part_a_change);
            $('#discipline-span').show();
          }
        });
        return;
      }
    }

    if (institution === 'none' || discipline === 'none' || course_groups.length === 0)
    {
      course_list = [];
      update_course_count();
      return;
    }

    // Create course_groups_string from the array.
    let ranges_str = '';
    for (let cg = 0; cg < course_groups.length; cg++)
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
    // Trim trailing semicolon
    ranges_str = ranges_str.substring(0, ranges_str.length - 1);

    // Get all course_ids for courses within one of the ranges for the given discipline at an
    // institution.
    const find_course_ids_request = $.getJSON($SCRIPT_ROOT + '/_find_course_ids',
      {
        institution: institution,
        discipline: discipline,
        ranges_str: ranges_str
      });
    find_course_ids_request.done(function (result, status)
    {
      if (status !== 'success')
      {
        alert(status);
      }
      else
      {
        course_list = result;
        update_course_count();
      }
    });
  };

  /* Clear string of course IDs, update num courses msg, and disable action buttons.
   */
  $('#clear-ids').mouseup(function ()
  {
    $('#course-ids').val('');
    $('#show-sending, #show-receiving').prop('disabled', true);
    $('#num-courses').text('No courses');
    course_list = [];
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

  /* Show Setup
   */
  $('#show-setup').mouseup(function ()
  {
    $('#pop-up-div').hide();
    $('#transfers-map-div').hide();
    $('#setup-div').show();
  });


  /*  Show Receiving and Show Sending event handlers
   *  ---------------------------------------------------------------------------------------------
   */
  const show_handler = function ()
  {
    const request_type = $(this).attr('id');
    if (request_type === 'show-receiving')
    {
      $('.to-from').text('from');
      $('.left-right').text('right');
    }
    else
    {
      $('.to-from').text('to');
      $('.left-right').text('left');
    }

    // Header row: "Sending" or "Receiving" Course and list of receiving colleges
    let colleges = [];
    const associates = $('#associates').prop('checked');
    const bachelors = $('#bachelors').prop('checked');
    for (let i = 0; i < institutions.length; i++)
    {
      if ((institutions[i].bachelors && bachelors) ||
          (institutions[i].associates && associates))
      {
        colleges.push(institutions[i]);
      }
    }

    let header_row = `<thead><tr>
                        <th rowspan="2" id="target-course-col">Sending Course</th>
                        <th colspan="${colleges.length}">Receiving College</th></tr>`;
    if (request_type === 'show-receiving')
    {
      header_row = `<thead>
                      <tr>
                      <th colspan="${colleges.length}">Sending College</th>
                      <th rowspan="2" id="target-course-col">Receiving Course</th></tr>`;
    }
    let colleges_row = '<tr>';
    for (let c = 0; c < colleges.length; c++)
    {
      let abbr = colleges[c].code.replace('01', '');
      colleges_row += `<th title="${colleges[c].name}" id="${abbr.toLowerCase()}-col">${abbr}</th>`;
      colleges[c] = colleges[c].code;
    }
    colleges_row += '</tr></thead><tbody>';
    // Get the table body rows from /_map_course
    $('#show-sending, #show-receiving').prop('disabled', true);
    $('#loading').show();
    const map_request = $.getJSON($SCRIPT_ROOT + '/_map_course',
      {
        course_list: JSON.stringify(course_list),
        discipline: $('#discipline').val(),
        colleges: JSON.stringify(colleges),
        request_type: $(this).attr('id')
      });
    map_request.done(function (result, status)
    {
      if (status !== 'success')
      {
        alert(status);
      }
      else
      {
        $('#loading').hide();
        $('#show-sending, #show-receiving').prop('disabled', false);
        $('#transfers-map-table').html(header_row + colleges_row + result + '</tbody>');
        $('#setup-div').hide();
        $('#transfers-map-div').show();
        let transfers_map_table = document.getElementById('transfers-map-table');
        let the_table = new ScrollableTable({table: transfers_map_table});
        let set_height = the_table.get_height_callback();

        // Will need to adjust height of the mapping table whenever the viewport is resized ...
        window.addEventListener('resize', set_height);
        // ... and when the details elemet opens or closes.
        const details = document.getElementsByTagName('details');
        if (details)
        {
          for (let i = 0; i < details.length; i++)
          {
            details[i].addEventListener('toggle', set_height);
          }
        }


      }

      // Event handlers for this table
      // ==========================================================================================

      // Clicking on a selected course pops up the catalog description
      // ------------------------------------------------------------------------------------------
      $('.selected-course').click(function ()
      {
        const title_string = $(this).attr('title');
        const matches = title_string.match(/course_id (\d+):/);
        const course_id = matches[1];
        const catalog_request = $.getJSON($SCRIPT_ROOT + '/_courses', {course_ids: course_id});
        catalog_request.done(function (result, status)
        {
          if (status !== 'success')
          {
            alert(status);
          }
          else
          {
            pop_up_content = result[0].html;
            $('#pop-up-content').html(pop_up_content);
            $('#pop-up-div').show().draggable();
          }
        });
      });

      //  Clicking on a data cell pops up a description of all the rules, if there are any.
      //  ---------------------------------------------------------------------------------
      $('td').click(function ()
      {
        if ($(this).text() !== '0')
        {
          $(document.body).css({cursor: 'wait'});
          const title_string = $(this).attr('title');
          if (title_string === '')
          {
            $('#pop-up-div').hide();
            return;
          }
          const rules_to_html_request = $.getJSON($SCRIPT_ROOT + '/_rules_to_html',
            {
              rule_keys: title_string
            });
          rules_to_html_request.done(function (result, status)
          {
            if (status !== 'success')
            {
              alert(status);
            }
            else
            {
              let html = result.replace(/<hr>/gi, '');
              // Remove the last cell of each row
              // DOES NOT WORK:
              // html = html.replace(/<td>.+?<\/td>[\s\S]<\/tr>/gi, '</tr>');
              $(document.body).css({cursor: 'auto'});
              pop_up_content = `<div><strong>Double-click a rule for catalog info.
              Type ⇦ to return here; Esc to dismiss this panel.</strong></div>
              <table>${html}</table>`;
              $('#pop-up-content').html(pop_up_content);
              $('#pop-up-div').show().draggable();
            }
          });
        }
      });
    });
  };
  $('#show-receiving, #show-sending').mouseup(show_handler);
  $('#show-receiving, #show-sending').keypress(show_handler);

  //  Double-clicking on a rule in the pop-up brings up the catalog descriptions for the courses
  //  involved in that same pop-up. Back arrow takes you back to the list of rules.
  //  -----------------------------------------------------------------------------------
  /*  The row id is rule_key-source_ids-dest_ids
   */
  $('#pop-up-content').dblclick(function (event)
  {
    // Find row id
    let target = event.target;
    while (target.tagName !== 'TR' && target.tagName !== 'BODY')
    {
      target = target.parentNode;
    }
    if (target.tagName !== 'TR')
    {
      return;
    }
    let row_id = target.id;

    // split it by hyphens
    let hyphenated = row_id.split('-');
    // source and dest ids
    let source_ids = hyphenated[4];
    let destination_ids = hyphenated[5];
    let suffix = (source_ids.indexOf(':') === -1) ? '' : 's';
    let source_heading = `${hyphenated[0].replace(/\d+/, '')} Course${suffix}`;
    suffix = (destination_ids.indexOf(':') === -1) ? '' : 's';
    let destination_heading = `${hyphenated[1].replace(/\d+/, '')} Course${suffix}`;
    // Clear the pop-up and request catalog info for source and dest courses
    $('#pop-up-content').html(`<div id="catalogs-for-rule">
                                <div>${source_heading}
                                  <div id="source-catalog-info">Loading ...</div>
                                </div>
                                <div>${destination_heading}
                                  <div id="destination-catalog-info">Loading ...</div>
                                </div>
                              </div>`);
    let source_request = $.getJSON($SCRIPT_ROOT + '/_courses', {course_ids: source_ids});
    let dest_request = $.getJSON($SCRIPT_ROOT + '/_courses', {course_ids: destination_ids});
    // when they come back, populate the pop-up
    // Populate the source catalog entries in the review form when they arrive
    source_request.done(function (data, status)
    {
      if (status !== 'success')
      {
        alert(status);
      }
      else
      {
        let html_str = '';
        for (let i = 0; i < data.length; i++)
        {
          html_str += `${data[i].html} <hr/>`;
        }
        $('#source-catalog-info').html(html_str);
      }
    });

    // Populate the destination catalog entries in the review form when they arrive
    dest_request.done(function (data, status)
    {
      if (status !== 'success')
      {
        alert(status);
      }
      else
      {
        let html_str = '';
        for (let i = 0; i < data.length; i++)
        {
          html_str += `${data[i].html}<hr/>`;
        }
        $('#destination-catalog-info').html(html_str);
      }
    });
  });
});
