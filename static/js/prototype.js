
$(function ()
 {
    var gapi_delay = 0;
    $('#need-js').innerHTML = '';
    $('#need-js').hide();
    $('#content-div').hide();
    $('#not-implemented-popup').hide();
    $('.not-implemented').click(function ()
    {
      $('#not-implemented-popup').show(200).delay(1000).hide(500);
    });

    var delay_period = 1500;
    var interval_id = null;
    var timeout_id = null;

    // check_app_start()
    // ----------------------------------------------------------------------------------
    function check_app_start()
    {
      window.clearTimeout(timeout_id);
      document.getElementById('error-msg').innerHTML = '';
      var app_started = document.getElementById('need-js').getAttribute('data-app-started');
      console.log('check_app_start: ', app_started, interval_id, timeout_id);
      if (app_started !== 'undefined')
      {
        $('#need-js').html('<p>No need to call <em>appStart().</em></p>')
                     .delay(delay_period)
                     .hide(delay_period);
      }
      else
      {
        $('#need-js').html('<p>Calling <em>appStart().</em></p>')
                     .delay(delay_period)
                     .hide(delay_period);
        appStart();
      }
    }
    // wait_for_api()
    // ----------------------------------------------------------------------------------
    function wait_for_gapi()
    {
      if (typeof gapi !== 'undefined')
      {
        // The wait is over. Cancel this interval and wait to be sure appStart got called
        console.log('gapi is now defined', interval_id, timeout_id);
        window.clearInterval(interval_id);
        document.getElementById('error-msg').innerHTML = '<p>Google API loaded okay.</p>';
        $('#need-js').html('<p>Google API is loaded. Checking appStart</p>');
        timeout_id = window.setTimeout(check_app_start, delay_period);
      }
      else
      {
        console.log('waiting for gapi, which is ', typeof gapi, interval_id, timeout_id);
        gapi_delay += delay_period;
        $('#need-js').html('<p>Waiting for Google API to load. (' +
          Number(gapi_delay / 1000).toLocaleString('EN-us', {minimumFractionDigits: 1}) +
          ' sec)</p>').show();
      }
    }

    //  Loading gapi is supposed to trigger a call to appStart, but it doesn't seem to happen
    //  on the iPad. So the following code tries to deal with that by waiting for gapi to be
    //  defined and then calling appStart() if it hasn't already run.
    console.log('prototype.js: appStart is ', typeof appStart);
    console.log('prototype.js: gapi is ', typeof appStart);
    var typeof_appstart = 'type ' + typeof appStart;
    var is_gapi = typeof gapi;
    console.log('is_gapi', is_gapi);
    if (is_gapi === 'undefined')
    {
      interval_id = window.setInterval(wait_for_gapi, delay_period);
      var is_app_started = document.getElementById('need-js').getAttribute('data-app-started');
    }
 });
