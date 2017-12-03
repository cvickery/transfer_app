/* This script handles all 3+ steps of the transfer review application.
 * as such, it should probably be broken up into separate scripts to avoid cross-step code
 * pollution. One reason it works is that there is no consequences for hooking code to elements
 * that don't actually exist in a particular step's DOM.
 * For now it continues its monolithic megopoly.
 */

$(function ()
{
  $('#need-js').hide();
  $('#evaluation-form').hide();
  $('#verification-details').hide();

  // Global action: escape key hides dialogs, currently only the evaluation-panel in form 2.
  $('*').keyup(function (event)
  {
    if (event.keyCode === 27)
    {
      $('.rule').removeClass('selected-rule');
      $('#evaluation-form').hide();
    }
  });

  var error_msg = '';
  var dismiss_bar = '<div id="dismiss-bar" class="dismiss">×</div>';
  var pending_evaluations = [];

  // Form #1 Select Colleges
  // ==============================================================================================
  /* Presented with a lists of all institutions, user has to select one sender and 1+ receivers or
   * vice-versa. Must supply a valid CUNY email address.
   */
  $('#submit-form-1').prop('disabled', true).css('color', '#cccccc');

  $('#all-sources, #all-destinations').prop('disabled', false);
  $('#no-sources, #no-destinations').prop('disabled', false);
  var ok_to_submit_1 = error_msg === '';

  // validate_form_1()
  // ----------------------------------------------------------------------------------------------
  function validate_form_1()
  {
    error_msg = '';
    var num_source = $('.source:checked').length;
    var num_dest = $('.destination:checked').length;
    var valid_email = /^\s*\w+(.\w+)*@(\w+\.)*cuny.edu\s*$/i.test($('#email-text').val());

    //  Check number of institutions selected
    if ((num_source === 1 && num_dest > 0) ||
        (num_source > 0 && num_dest === 1))
    {
      error_msg = '';
    }
    else
    {
      error_msg += '<p>You must select either a single sending college and one or more ' +
                   'receiving colleges or a single receiving college and one or more ' +
                   'sending colleges.</p>';
    }

    //  Check CUNY email address
    /*  It's an error if value is not blank, otherwise it's a warning. But in either case, the
     *  form can't be submitted yet.
     */
    bg_color = '#ffffff';
    if (!valid_email)
    {
      if ($('#email-text').val() !== '')
      {
        // User entered an invalid email
        bg_color = '#ff9999'; // error
        if (error_msg === '')
        {
          error_msg = '<p>You must supply a valid CUNY email address.</p>';
        }
      }
      else
      {
        // No email yet
        bg_color = '#ffffcc'; // warning
        if (error_msg === '')
        {
          // Valid selections with no email: prompt for it
          error_msg = '<p>Enter your CUNY email address.</p>';
        }
      }
    }

    $('#email-text').css('background-color', bg_color);

    $('#error-msg').html(error_msg);
    ok_to_submit_1 = error_msg === '';
    if (ok_to_submit_1)
    {
      $('#submit-form-1').prop('disabled', false).css('color', '#000000');
    }
    else
    {
      $('#submit-form-1').prop('disabled', true).css('color', '#cccccc');
    }
  }

  // Form 1: clear or set groups of checkboxes
  // ----------------------------------------------------------------------------------------------
  $('#all-sources').click(function (event)
  {
    $('.source').prop('checked', true);
    validate_form_1();
  });

  $('#no-sources').click(function (event)
  {
    $('.source').prop('checked', false);
    validate_form_1();
  });

  $('#all-destinations').click(function ()
  {
    $('.destination').prop('checked', true);
    validate_form_1();
  });

  $('#no-destinations').click(function ()
  {
    $('.destination').prop('checked', false);
    validate_form_1();
  });

  // If any checkbox or the email text changes, validate the form
  $('input').change(function ()
  {
    validate_form_1();
  });

  // Form 1: Submit the form. Maybe.
  // ----------------------------------------------------------------------------------------------
  var submit_button_1 = false;
  $('#form-1').submit(function (event)
  {
    return submit_button_1;
  });

  $('#submit-form-1').click(function (event)
  {
    submit_button_1 = true;
  });

  // Form 2 Select Disciplines
  // ==============================================================================================
  /* Given a list of sending and receiving offered disciplines, grouped by CUNY subject names, the
   * The user must select at least one discipline group from the sending column and at least one
   * from the receiving column. Convenience boxes let the user clear or select all items in a
   * column.
   */

  // Form 2: Manage checkboxes
  // ----------------------------------------------------------------------------------------------

  $('.f2-cbox').has('input').css('background-color', 'white');
  $('#all-sending-subjects').click(function ()
  {
    $('.source-subject input:checkbox').prop('checked', true);
    $('#no-sending-subjects').prop('checked', false);
  });
  $('#no-sending-subjects').click(function ()
  {
    $('.source-subject input:checkbox').prop('checked', false);
  });

  $('#all-receiving-subjects').click(function ()
  {
    $('.destination-subject input:checkbox').prop('checked', true);
    $('#no-receiving-subjects').prop('checked', false);
  });
  $('#no-receiving-subjects').click(function ()
  {
    $('.destination-subject input:checkbox').prop('checked', false);
  });

  //  Form 2: Hide instructions
  // ----------------------------------------------------------------------------------------------
  $('.instructions').click(function()
  {
    var this_height = $(this).height();
    $(this).hide();
    $('.selection-table-div').height($('.selection-table-div').height() + this_height);
  });



  //  Form 3 Validation and Processing
  //  =============================================================================================
  $('.rule').click(function (event)
  {
    // clicks in the prior evaluations column do not select a rule.
    if (event.target.nodeName === 'A')
    {
      return;
    }

    $('.rule').removeClass('selected-rule');
    $(this).addClass('selected-rule');
    var rule_str = '';
    $(this).find('td').each(function (index)
    {
      rule_str += $(this).text() + ' ';
    });

    // Rule ids: "source_course_id:source_institution:dest_course_id:dest_institution"
    // New Row IDs: rule_id; hyphen;
    //              source institution name; hyphen;
    //              colon-separated list of source course IDs, hyphen,
    //              destination institution name; hyphen;
    //              colon-separated list of destination course IDs.
    //
    var row_id = $(this).attr('id');
    var row_html = document.getElementById(row_id).innerHTML;
    var rule_table = `<table><tr>${row_html}</tr></table>`;

    var first_parse = row_id.split('-');
    var rule_id = first_parse[0];
    var source_institution = first_parse[1].replace(/_/g, ' ');
    var source_course_ids = first_parse[2].split(':');
    var destination_institution = first_parse[3].replace(/_/g, ' ');
    var destination_course_ids = first_parse[4].split(':');
    var source_request = $.getJSON($SCRIPT_ROOT + '/_courses', {course_ids: first_parse[2]});
    var dest_request = $.getJSON($SCRIPT_ROOT + '/_courses', {course_ids: first_parse[4]});

    var source_suffix = (source_course_ids.length !== 1) ? 's' : '';
    var source_catalog_div = `<div id="source-catalog-div">
                              <h2>${source_institution} Course${source_suffix}</h2>
                              <div id="source-catalog-info">
                                <p>Waiting for catalog entries ...</p>
                                </div>
                            </div>`;
    var destination_suffix = (destination_course_ids.length !== 1) ? 's' : '';
    var destination_catalog_div = `<div id="destination-catalog-div">
                                  <h2>${destination_institution} Course${destination_suffix}</h2>
                                  <div id="destination-catalog-info">
                                    <p>Waiting for catalog entries ...</p>
                                    </div>
                                </div>`;

    var controls = `<div id="evaluation-controls-div" class="clean">
                    <div>
                      <input type="radio" name="reviewed" id="src-ok" value="src-ok"/>
                      <label for="src-ok">Verified by ${source_institution}</label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="src-not-ok" value="src-not-ok"/>
                      <label for="src-not-ok">Problem observed by ${source_institution}</label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="dest-ok" value="dest-ok"/>
                      <label for="dest-ok">
                        Verified by ${destination_institution}
                      </label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="dest-not-ok" value="dest-not-ok"/>
                      <label for="dest-not-ok">
                        Problem observed by ${destination_institution}
                      </label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="other" value="other"/>
                      <label for="other">Other</label>
                    </div>
                    <textarea id="comment-text"
                              placeholder="Explain problem or “Other” here."
                              minlength="12" />
                    <input type="hidden" name="src_institution"
                           value="${source_institution}" />
                    <input type="hidden" name="dest_institution"
                           value="${destination_institution}" />
                    <input type="hidden" name="rule-id" value="${rule_id}" />
                    <button class="ok-cancel" id="review-submit" type="button" disabled="disabled">OK</button>
                    <button class="ok-cancel dismiss" type="button">Cancel</button>
                  </div>`;
    $('#evaluation-form').html(dismiss_bar +
                               rule_table +
                               source_catalog_div +
                               destination_catalog_div +
                               controls)
                           .show()
                           .draggable();




    source_request.done(function (data, text_status)
    {
//      console.log(`source status: ${text_status}`);
      var html_str = '';
      for (var i = 0; i < data.length; i++)
      {
        html_str += `${data[i].html} ${data[i].note} <hr/>`
      }
      $('#source-catalog-info').html(html_str);
    });
    dest_request.done(function (data, text_status)
    {
      //      console.log(`destination status: ${text_status}`);
      var html_str = '';
      for (var i = 0; i < data.length; i++)
      {
        html_str += `${data[i].html} ${data[i].note} <hr/>`
      }
      $('#destination-catalog-info').html(html_str);
    });
    $.when(source_request, dest_request).done(function (source_request, dest_request)
    {

      var evaluation_form = document.getElementById('evaluation-form');
      var eval_form_rect = evaluation_form.getBoundingClientRect();
      evaluation_form.style.position = 'fixed';
      evaluation_form.style.top = ((window.innerHeight / 2) - (eval_form_rect.height / 2)) + 'px';
      evaluation_form.style.left = ((window.innerWidth / 2) - (eval_form_rect.width / 2)) + 'px';
      $('.dismiss').click(function ()
      {
        $('.rule').removeClass('selected-rule');
        $('#evaluation-form').hide();
      });
        // Enable form submission only if an input has changed.
        $('input').change(setup_ok_to_submit);
        $('textarea').keyup(setup_ok_to_submit);
        function setup_ok_to_submit()
        {
          var comment_len = $('#comment-text').val().length;
          var ok_to_submit = ($(this).attr('id') === 'src-ok' ||
                              $(this).attr('id') === 'dest-ok' ||
                              comment_len > 12);
          $('#review-submit').attr('disabled', !ok_to_submit);
        }

        // Process evaluation info if submitted
        $('#review-submit').click(function (event)
        {
          pending_evaluations.push(
          {
            event_type: $('input[name=reviewed]:checked').val(),
            source_institution: $('input[name=src_institution]').val(),
            destination_institution: $('input[name=dest_institution]').val(),
            comment_text: $('#comment-text').val().replace('\'', '’'),
            rule_src_id: source_id,
            rule_dest_id: destination_id,
            rule_index: rule_index,
            rule_str: rule_str,
            is_omitted: false
          });
          $('.selected-rule').addClass('evaluated');

          // Update the evaluations pending information
          var num_pending = pending_evaluations.length;
          var num_pending_text = $('#num-pending').text();
          if (num_pending_text === 'are no evaluations')
          {
            num_pending_text = 'is one evaluation';
          }
          else
          {
            if (num_pending_text === 'is one evaluation')
            {
              num_pending = 2;
            }
            else
            {
              // Extract the current count from the text and increment it
              var m = num_pending_text.match(/\d+/);
              num_pending = parseInt(m) + 1;
            }
            num_pending_text = `are ${num_pending} evaluations`;
          }
          $('#num-pending').text(num_pending_text);
          $('#evaluation-form').hide();
          $('#verification-details').show();

          // Enable review/send-email button
          $('#send-email').attr('disabled', false);
          event.preventDefault(); // don't actually submit the form to the server.
        });
      });
    });

    // Review and send email button click
    // --------------------------------------------------------------------------------------------
    /* Generate a form for reviewing the evaluations so the user can omit items they don't
     * intend. Then submit the form to a web page that actually enters the items into the pending_evaluations
     * table and sends email to the user.
     */
    $('#send-email').click(function (event)
    {
      var email_address = $('#email-address').text();
      var the_form = `
        <fieldset id="review-form">
          <h2>Review Your Evaluations</h2><p>Use the buttons to omit (or include) items.</p>
          <div id='evaluations-list'>
        `;
      for (evaluation in pending_evaluations)
      {
        var the_rule = pending_evaluations[evaluation].rule_src_id + ':' +
                       pending_evaluations[evaluation].rule_dest_id;
        var institution = 'Unknown';
        var go_nogo = 'Unknown';
        switch (pending_evaluations[evaluation].event_type)
        {
          case 'src-ok':
            institution = pending_evaluations[evaluation].source_institution;
            go_nogo = 'OK';
            break;
          case 'dest-ok':
            institution = pending_evaluations[evaluation].destination_institution;
            go_nogo = 'OK';
            break;
          case 'src-not-ok':
            institution = pending_evaluations[evaluation].source_institution + ': ';
            go_nogo = pending_evaluations[evaluation].comment_text;
            break;
          case 'dest-not-ok':
            institution = pending_evaluations[evaluation].destination_institution + ': ';
            go_nogo = pending_evaluations[evaluation].comment_text;
            break;
          default:
            institution = 'Other: ';
            go_nogo = pending_evaluations[evaluation].comment_text;
            break;

        }
        the_form += `<div id="eval-rule-${the_rule}" class="eval-rule">
          <button type="button" id="omit-eval-${the_rule}" class="omit-button">Omit</button>
          <span id="rule-${the_rule}">${pending_evaluations[evaluation].rule_str}<br/>${institution} ${go_nogo}</span>
          </div>`;
      }
      the_form += '</div><input type="hidden" value="${email_address}" />';
      the_form += `
          <input type="hidden" name="next-function" value="do_form_3" />
          <input type="hidden" id="hidden-evaluations" name="evaluations" value="Not Set" />
          <button class="ok-cancel" type="submit">Submit These Evaluations</button>
          <button class="ok-cancel dismiss" type="button">Cancel</button>
          </fieldset>
        `;
      $('#evaluation-form').html(dismiss_bar + the_form)
                           .css('width', '90%')
                           .show().draggable();
      $('.omit-button').click(function ()
      {
        // extract the button's rule-index and use it to gray out the div containing it and to mark
        // the evaluation as disabled.
        var rule_index = $(this).attr('id').split('-')[2];
        var omit_div_id = 'eval-rule-' + rule_index.replace(':', '\\:');
        for (evaluation in pending_evaluations)
        {
          if (pending_evaluations[evaluation].rule_index == rule_index)
          {
            if (pending_evaluations[evaluation].is_omitted)
            {
              $('#' + omit_div_id).removeClass('omitted');
              pending_evaluations[evaluation].is_omitted = false;
              $(this).text('Included');
            }
            else
            {
              $('#' + omit_div_id).addClass('omitted');
              pending_evaluations[evaluation].is_omitted = true;
              $(this).text('Omitted');
            }
            break;
          }
        }
      });

      $('#evaluation-form').submit(function ()
      {
        $('input[name="evaluations"]').val(JSON.stringify(pending_evaluations));
      });
      var evaluation_form = document.getElementById('evaluation-form');
      var eval_form_rect = evaluation_form.getBoundingClientRect();
      evaluation_form.style.position = 'fixed';
      evaluation_form.style.top = ((window.innerHeight / 2) - (eval_form_rect.height / 2)) + 'px';
      evaluation_form.style.left = ((window.innerWidth / 2) - (eval_form_rect.width / 2)) + 'px';
      $('.dismiss').click(function ()
      {
        $('#evaluation-form').hide();
      });
    });
  });

