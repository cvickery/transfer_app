$(function ()
{
  $('#need-js').hide();

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
        if (error_msg  === '')
        {
          // Valid selections with no email: prompt for it
          error_msg = '<p>Enter your CUNY email address.</p>'
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
  $('#all-sources').click(function ()
  {
    $('.source').prop('checked', true);
    validate_form_1();
  });

  $('#no-sources').click(function ()
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

  $('input').change(function ()
  {
    validate_form_1();
  });

  // Form 1: Submit the form. Maybe.
  // ----------------------------------------------------------------------------------------------
  var submit_button_1 = false;
  $('#form-1').submit(function (event)
  {
    console.log('form-1 submit with submit_button_1 = ' + submit_button_1)
    return submit_button_1;
  });

  $('#submit-form-1').click(function (event)
  {
    console.log('submit-form-1 click')
    submit_button_1 = true;
  });

  // Form 2: Manage checkboxes
  $('#all-subjects').click(function ()
  {
    $('input:checkbox').prop('checked', true);
    $('#all-subjects, #no-subjects').prop('checked', false);
  });
  $('#no-subjects').click(function ()
  {
    $('input:checkbox').prop('checked', false);
  });

});
