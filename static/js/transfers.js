$(function ()
{
  $('#need-js').hide();

  var error_msg = '';

  // Form #0 Validation
  // ==============================================================================================
  $('#submit-form-0').prop('disabled', true);

  $('#all-sources, #all-destinations').prop('disabled', false);
  $('#no-sources, #no-destinations').prop('disabled', false);
  var ok_to_submit_0 = error_msg === '';

  // validate_form_0()
  // ----------------------------------------------------------------------------------------------
  function validate_form_0()
  {
    var num_source = $('.source:checked').length;
    var num_dest = $('.destination:checked').length;
    var valid_email = /^\w+(.\w+)*@(\w+\.)*cuny.edu$/i.test($('#email-text').val());


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
    bg_color = '#ffffff';
    if (!valid_email)
    {
      if (error_msg === '')
      {
        // Valid selections: invalid email is an error
        bg_color = '#ff0000';
        error_msg += '<p>You must supply a valid CUNY email address.</p>';
      }
      else
      {
        // Invalid selections: invalid email is a warning
        bg_color = '#ffffcc';
      }
    }
    $('#email-text').css('background-color', bg_color);

    $('#error-msg').html(error_msg);
    ok_to_submit_0 = error_msg === '';
    $('#submit-form-0').prop('disabled', !ok_to_submit_0);
  }

  // Form 0: clear or set groups of checkboxes
  // ----------------------------------------------------------------------------------------------
  $('#all-sources').click(function ()
  {
    $('.source').prop('checked', true);
    validate_form_0();
  });

  $('#no-sources').click(function ()
  {
    $('.source').prop('checked', false);
    validate_form_0();
  });

  $('#all-destinations').click(function ()
  {
    $('.destination').prop('checked', true);
    validate_form_0();
  });

  $('#no-destinations').click(function ()
  {
    $('.destination').prop('checked', false);
    validate_form_0();
  });

  $('input:checkbox').change(function ()
  {
    validate_form_0();
  });

  // Form 0: Submit the form. Maybe.
  // ----------------------------------------------------------------------------------------------
  var submit_button_0 = false;
  $('#form-0').submit(function (event)
  {
    return submit_button_0;
  });

  $('#submit-form-0').click(function (event)
  {
    submit_button_0 = true;
  });

});
