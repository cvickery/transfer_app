$(function ()
{
  $('#need-js').hide();
  $('button').prop('disabled', true);

  $('input').change(function ()
  {
    $('button').prop('disabled', false);
  });
});
