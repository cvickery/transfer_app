$(function ()
{
  $('#need-js').hide();

  $('button').prop('disabled', true);

  $('input').change(function ()
  {
    $('button').prop('disabled', false);
  });

  // Global action: escape key hides pop-ups; question key shows instructions.
  $('*').keyup(function (event)
  {
    if (event.keyCode === 27)
    {
      $('#pop-up-div').hide();
    }
    if (event.key === '?')
    {
      $('.instructions').show();
    }
  });

  // Clicking on the dismiss bar also hides the pop-ups.
  $('#dismiss-bar').click(function ()
  {
    $('#pop-up-div').hide();
  });

  // Clicking on the instructions hides them.
  $('.instructions').click(function ()
  {
    $(this).hide();
  });

  $('#show-attributes').click(function (e)
  {
    e.stopPropagation();
    $('#pop-up-div').show().draggable();
    $('#pop-up-inner').resizable();
  });

});
