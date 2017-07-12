$(function ()
{
  var ok_to_submit = false;
  function validate_form()
  {
    var valid_source = $('.source:checked').length > 0;
    var valid_dest = $('.destination:checked').length > 0;
    var valid_subj = true;
    var valid_email = /^\w+(.\w+)*@(\w+\.)*cuny.edu$/i.test($('#email-text').val());
    if (valid_source && valid_dest && valid_subj && valid_email)
    {
      ok_to_submit = true;
    }
    else
    {
      ok_to_submit = false;
      $('button[type="submit"]').prop('disabled', true);
    }
    $('button[type="submit"]').prop('disabled', false);

    bg_color = '#ffffff';
    if (!valid_email)
    {
      if (valid_source && valid_dest && valid_subj)
      {
        bg_color = '#ff0000';
      }
      else
      {
        bg_color = '#ffffcc';
      }
    }
    $('#email-text').css('background-color', bg_color);
  }
  $('#need-js').hide();
  $('button').prop('disabled', true);

  $('#no-sources, #no-destinations').prop('disabled', false);
  $('#all-sources, #all-destinations').prop('disabled', false);

  $('#all-sources').click(function ()
  {
    $('.source').attr('checked', true);
  });

  $('#no-sources').click(function ()
  {
    $('.source').attr('checked', false);
  });

  $('#all-destinations').click(function ()
  {
    $('.destination').attr('checked', true);
  });

  $('#no-destinations').click(function ()
  {
    $('.destination').attr('checked', false);
  });

  $('input').change(function ()
  {
    validate_form();
  });
  $('form').submit(function (event)
  {
    validate_form();
    alert('submitting ' + ok_to_submit);
    event.preventDefault();
  });
});
