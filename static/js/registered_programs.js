$(function()
{
  //  Submit button not needed if JS is running ’cause this code does it automatically.
  //  But people want to see it, so just disable it.
  // $('#submit-button').hide();
  $('select').change(function()
  {
    $('form').submit();
  });
});
