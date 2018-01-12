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
    if (catalog_number === '')
    {
      return;
    }
    var discipline = $('#discipline').val();
    if (discipline === 'none')
    {
      return;
    }
    var institution = $('#institution').val();
    if (institution === 'none')
    {
      return;
    }

    var sending = false;
    var receiving = false;
    $('#sending-rules').html('');
    $('#receiving-rules').html('');
    switch ($('input[name=which-rules]:checked').val())
    {
      case '1':
          sending = true;
          break;
      case '2':
          receiving = true;
          break;
      case '3':
          sending = true;
          receiving = true;
          break;
      default:
          alert('Bad Switch');
    }

    if (sending)
    {
      $('#sending-rules').html('<p>Searching &hellip;</p>');
      var sending_request = $.getJSON($SCRIPT_ROOT + '/_lookup_rules',
                                  { institution: institution,
                                    discipline: discipline,
                                    catalog_number: catalog_number,
                                    type: 'sending'
                                  });
      sending_request.done(function (rules, text_status)
      {
        if (text_status === 'success')
        {
          $('#sending-rules').html(rules);
        }
        else
        {
          $('#sending-rules').html('<p class="error">Search Failed</p>');
        }
      });
    }

    if (receiving)
    {
      $('#receiving-rules').html('<p>Searching &hellip;</p>');
      var receiving_request = $.getJSON($SCRIPT_ROOT + '/_lookup_rules',
                                  { institution: institution,
                                    discipline: discipline,
                                    catalog_number: catalog_number,
                                    type: 'receiving'
                                  });
      receiving_request.done(function (rules, text_status)
      {
        if (text_status === 'success')
        {
          $('#receiving-rules').html(rules);
        }
        else
        {
          $('#receiving-rules').html('<p class="error">Search Failed</p>');
        }
      });
    }
  });
});
