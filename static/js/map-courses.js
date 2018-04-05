$(function ()
{
  //  Initial Settings
  //  =============================================================================================
  $('#need-js').hide();
  $('#transfers-map-div').hide();
  $('form').submit(function (event)
  {
    event.preventDefault();
  });
  $('#show-sending, #show-receiving').prop('disabled', true);

  //  Event Listeners
  //  =============================================================================================
  /* Change college: update disciplines selection
   */
  $('#institution').change(function ()
  {
    var institution = $('#institution').val();
    if (institution !== 'none')
    {
      var discipline_request = $.getJSON($SCRIPT_ROOT + '/_disciplines',
                                         {institution: institution});
      discipline_request.done(function (discipline_select, text_status)
      {
        $('#discipline').replaceWith(discipline_select);
      });
    }
  });

  /* Clear list of course IDs
   */
  $('#clear-ids').click(function()
  {
    $('#course-ids').val('');
  });
});
