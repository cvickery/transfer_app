$(function ()
{
  //  Submit button not needed if JS is running...
  $('#submit-button').hide();
  // ... ’cause this code does it automatically.
  $('select').change(function ()
  {
    if ($(this).value != 'none')
    {
      $('form').submit();
    }
  });
});