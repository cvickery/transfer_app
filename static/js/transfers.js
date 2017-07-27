$(function ()
{
  $('#need-js').hide();
  $('#evaluation-form').hide();

  var error_msg = '';

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

  // If any checkbox changes, validate the form
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
    $('#all-sending-subjects-top, #no-sending-subjects-top, ' +
      '#all-sending-subjects-bot, #no-sending-subjects-bot').prop('checked', false);
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
    // Rule ids: source_course_id:source_institution:dest_course_id:dest_institution
    var this_rule = $(this).attr('id').split(':');
    var source_id = this_rule[0];
    var source_institution = this_rule[1];
    var destination_id = this_rule[2];
    var destination_institution = this_rule[3];
    var source_catalog = '';
    var destinaton_catalog = '';
    $.getJSON($SCRIPT_ROOT + '/_course', {course_id: source_id}, function (data)
    {
      source_catalog = '<div class="source-catalog"><h2>Sending Course</h2>' + data + '</div><hr/>';
    });
      $.getJSON($SCRIPT_ROOT + '/_course', {course_id: destination_id}, function (data)
      {
        destination_catalog = '<div class="destination-catalog"><h2>Receiving Course</h2>' +
                              data + '</div><hr/>';
        controls = `<fieldset id="rule-evaluation" class="clean">
                      <div>
                        <input type="radio" name="reviewed" id="src-ok"/>
                        <label for="src-ok">Verified by ${source_institution}</label>
                      </div>
                      <div>
                        <input type="radio" name="reviewed" id="src-not-ok"/>
                        <label for="src-not-ok">Problem observed by ${source_institution}</label>
                      </div>
                      <div>
                        <input type="radio" name="reviewed" id="dest-ok"/>
                        <label for="dest-ok">
                          Verified by ${destination_institution}
                        </label>
                      </div>
                      <div>
                        <input type="radio" name="reviewed" id="dest-not-ok"/>
                        <label for="dest-not-ok">
                          Problem observed by ${destination_institution}
                        </label>
                      </div>
                      <div>
                        <input type="radio" name="reviewed" id="other"/>
                        <label for="other">Other</label>
                      </div>
                      <textarea id="comment-text"
                                placeholder="Explain problem or “Other” here."
                                minlength="12" />
                      <input type="hidden" name="source-id" value="${source_id}" />
                      <input type="hidden" name="destination-id" value="${destination_id}" />
                      <button id="review-submit" type="button" disabled="disabled">Submit</button>
                    </fieldset>`;

        $('#evaluation-form').html(source_catalog + destination_catalog + controls).show();
        $('#rule-evaluation').css('background-color', '#ffffff');

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
          var num_pending = 0;
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
          $('#evaluation-form').html('');
          $('.selected-rule').addClass('evaluated');

          // *** Enter form data into db here ***

          // Enable verify button
          $('#send-email').attr('disabled', false);

          event.preventDefault(); // don't actually submit the form to the server.
        });
      });
  });

  // Send email
  $('#send-email').click(function ()
  {
    alert('Not implemented yet.');
  });
});
