$(function ()
{
  $('#need-js').hide();

  $('form').submit(function (event)
  {
    event.preventDefault();
  });

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
  $('#institution, #discipline, #catalog-number').change(function ()
  {
    var catalog_number = $('#catalog-number').val().trim();
    if (catalog_number === '') return;
    var discipline = $('#discipline').val();
    if (discipline === 'none') return;
    var institution = $('#institution').val();
    if (institution === 'none') return;

    var rule_request = $.getJSON($SCRIPT_ROOT + '/_lookup_rules',
                                 {institution: institution,
                                  discipline: discipline,
                                  catalog_number: catalog_number
                                });
    rule_request.done(function (rules, text_status)
    {
      console.log(rules);
      $('#sending-rules').html(rules.sending_rules);
      $('#receiving-rules').html(rules.receiving_rules);
    });
  });
});
