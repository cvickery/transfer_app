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
  $('*').keyup(function (event)
  {
    if (event.keyCode === 27)
    {
      $('#evaluation-form').hide();
    }
  });

  var error_msg = '';
  var dismiss_bar = '<div id="dismiss-bar">×</div>';
  var pending_evaluations = [];

  // Form #1 Validation
  // ==============================================================================================
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

  // Form 0: clear or set groups of checkboxes
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

  // Form 2: Manage checkboxes
  // ==============================================================================================
  $('#all-sending-subjects-top, #all-sending-subjects-bot').click(function ()
  {
    $('.source-subject input:checkbox').prop('checked', true);
    $('#no-sending-subjects-top, #no-sending-subjects-bot').prop('checked', false);
  });
  $('#no-sending-subjects-top, #no-sending-subjects-bot').click(function ()
  {
    $('.source-subject input:checkbox').prop('checked', false);
  });

  $('#all-receiving-subjects-top, #all-receiving-subjects-bot').click(function ()
  {
    $('.destination-subject input:checkbox').prop('checked', true);
    $('#no-receiving-subjects-top, #no-receiving-subjects-bot').prop('checked', false);
  });
  $('#no-receiving-subjects-top, #no-receiving-subjects-bot').click(function ()
  {
    $('.destination-subject input:checkbox').prop('checked', false);
  });

  //  Form 2: Clickable rules
  $('.rule').click(function (event)
  {
    $('.rule').removeClass('selected-rule');
    $(this).addClass('selected-rule');
    var rule_id = $(this)[0];
    // Rule ids: "source_course_id:source_institution:dest_course_id:dest_institution"
    var this_rule = $(this).attr('id').split(':');
    var source_id = this_rule[0];
    var source_institution = this_rule[1];
    var destination_id = this_rule[2];
    var destination_institution = this_rule[3];

    var source_catalog = '';
    var destinaton_catalog = '';

    source_request = $.getJSON($SCRIPT_ROOT + '/_course', {course_id: source_id});
    dest_request = $.getJSON($SCRIPT_ROOT + '/_course', {course_id: destination_id});
    source_request.done(function (data, text_status)
    {
//      console.log(`source status: ${text_status}`);
      source_catalog = `<div class="source-catalog">
        <h2>Sending Course</h2>
        ${data.institution}  / ${data.department} ${data.html} ${data.note}
        </div><hr/>`;
    });
    dest_request.done(function (data, text_status)
    {
//      console.log(`destination status: ${text_status}`);
      destination_catalog = `<div class="destination-catalog">
        <h2>Receiving Course</h2>
        ${data.institution}  / ${data.department} ${data.html} ${data.note}
        </div><hr/>`;
    });
    $.when(source_request, dest_request).done(function (source_request, dest_request)
    {
      controls = `<fieldset id="rule-evaluation" class="clean">
                    <div>
                      <input type="radio" name="reviewed" id="src-ok" value="src-ok"/>
                      <label for="src-ok">Verified by ${source_institution}</label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="src-not-ok" value="src-not-ok"/>
                      <label for="src-not-ok">Problem observed by ${source_institution}</label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="dest-ok" value=="dest-ok"/>
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
                      <input type="radio" name="reviewed" id="other" value"other"/>
                      <label for="other">Other</label>
                    </div>
                    <textarea id="comment-text"
                              placeholder="Explain problem or “Other” here."
                              minlength="12" />
                    <input type="hidden" name="source-id" value="${source_id}" />
                    <input type="hidden" name="destination-id" value="${destination_id}" />
                    <button id="review-submit" type="button" disabled="disabled">Submit</button>
                  </fieldset>`;

      $('#evaluation-form').html(dismiss_bar + source_catalog + destination_catalog + controls)
                           .show();
      var evaluation_form = document.getElementById('evaluation-form');
      var eval_form_rect = evaluation_form.getBoundingClientRect();
      evaluation_form.style.position = 'fixed';
      evaluation_form.style.top = ((window.innerHeight / 2) - (eval_form_rect.height / 2)) + 'px';
      evaluation_form.style.left = ((window.innerWidth / 2) - (eval_form_rect.width / 2)) + 'px';
      $('#dismiss-bar').click(function ()
      {
        $('#evaluation-form').hide();
      });
        // Enable form submission only if an input has changed.
        $('input, textarea').change(function ()
        {
          var comment_len = $('#comment-text').val().length;
          var ok_to_submit = ($(this).attr('id') === 'src-ok' ||
                              $(this).attr('id') === 'dest-ok' ||
                              comment_len > 12);
          $('#review-submit').attr('disabled', !ok_to_submit);
        });

        // Process evaluation info if submitted
        $('#review-submit').click(function (event)
        {
          // *** Enter form data into db here ***
          pending_evaluations.push(
          {
            event_type: $('input[name=reviewed]:checked').val(),
            comment_text: $('#comment-text').val(),
            rule_source_id: source_id,
            rule_destination_id: destination_id
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

          // Enable verify button
          $('#send-email').attr('disabled', false);
          event.preventDefault(); // don't actually submit the form to the server.
        });
      });
    });

    // Send email button click
    // --------------------------------------------------------------------------------------------
    /* Generate a form for reviewing the evaluations so the user can delete items they don't
     * intend. Then submit the form to a web page that actually enters the items into the "pending"
     * table and sends email to the user.
     */
    $('#send-email').click(function (event)
    {
      console.log(pending_evaluations);
      var email_address = $('#email-address').text();
      var the_form = `
        <fieldset>
          <h2>Instructions</h2><p>These are your instructions.</p>
          <form method="POST" action="">
        `;
      for (evaluation in pending_evaluations)
      {
        the_form += 'hello';
      }
      the_form += '<input type="hidden" value="${email_address}" />';
      the_form += `
          <input type="hidden" name="next-function" value="do_form_3" />
          <button type="submit">Submit These Evaluations</button>
          </form></fieldset>
        `;
      $('#evaluation-form').html(dismiss_bar + the_form)
                           .show();
      var evaluation_form = document.getElementById('evaluation-form');
      var eval_form_rect = evaluation_form.getBoundingClientRect();
      evaluation_form.style.position = 'fixed';
      evaluation_form.style.top = ((window.innerHeight / 2) - (eval_form_rect.height / 2)) + 'px';
      evaluation_form.style.left = ((window.innerWidth / 2) - (eval_form_rect.width / 2)) + 'px';
      $('#dismiss-bar').click(function ()
      {
        $('#evaluation-form').hide();
      });
      alert('Not fully implemented yet');
    });
  });

