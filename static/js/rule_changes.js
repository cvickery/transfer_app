
window.addEventListener('load', function()
{

  let archive_dates = [];
  let archive_date_strings = [];

  fetch('/_archive_dates')
    .then(something => something.json())
    .then(data =>
    {
      archive_dates = Object.getOwnPropertyNames(data);
      archive_date_strings = data;
    });

  const submit_button = document.getElementsByTagName('button')[0];
  const first_date = document.getElementById('first_date');
  const second_date = document.getElementById('second_date');
  const first_msg = document.querySelector('#first_date+span');
  const second_msg = document.querySelector('#second_date+span');
  if (submit_button)
  {
    first_date.addEventListener('change', first_changed);
    second_date.addEventListener('change', second_changed);
    submit_button.setAttribute('disabled', 'disabled');

  }

  //  first_changed()
  //  ---------------------------------------------------------------------------------------------
  function first_changed()
  {
    first_msg.innerText = '';
    first_msg.classList.remove('error');
    first_msg.classList.remove('warning');
    first_msg.classList.remove('good');

    if (first_date.value)
    {
      // find last archive before selected date, or earliest archive date if none.
      if (first_date.value < archive_dates[0])
      {
        first_msg.innerText = 'Using earliest archive available: ' +
                              archive_date_strings[archive_dates[0]];
        first_msg.classList.add('warning');
        first_date.value = archive_dates[0];
      }
      else
      {
        // Search
        let prev = archive_dates[0];
        for (let d in archive_dates)
        {
          if (archive_dates[d] === first_date.value)
          {
            first_msg.innerText = 'OK';
            first_msg.classList.add('good');
            break;
          }
          else if (archive_dates[d] > first_date.value)
          {
            first_msg.innerText = `Using last archive before ${first_date.value} — ` +
                                   archive_date_strings[archive_dates[prev]];
            first_msg.classList.add('warning');
            first_date.value = archive_dates[prev];
            break;
          }
          prev = d;
        }
      }
      if (first_msg.innerText === '')
      {
        first_msg.innerText = 'No matching archive available.';
        first_msg.classList.add('error');
        first_date.value = '';
      }
    }

    if (first_date.value && second_date.value)
    {
      submit_button.removeAttribute('disabled');
    }
    else
    {
      submit_button.setAttribute('disabled', 'disabled');
    }

  }

  //  second_changed()
  //  ---------------------------------------------------------------------------------------------
  function second_changed()
  {
    second_msg.innerText = '';
    second_msg.classList.remove('error');
    second_msg.classList.remove('warning');
    second_msg.classList.remove('good');
    const reversed_dates = archive_dates.reverse();

    if (second_date.value)
    {
      if (second_date.value > reversed_dates[0])
      {
        second_msg.innerText = 'Using most recent archive available: ' +
                               archive_date_strings[reversed_dates[0]];
        second_msg.classList.add('warning');
      }
      else
      {
        // Search
        let prev = reversed_dates[0];
        for (let d in reversed_dates)
        {
          if (reversed_dates[d] === second_date.value)
          {
            second_msg.innerText = 'OK';
            second_msg.classList.add('good');
            break;
          }
          else if (reversed_dates[d] > second_date.value)
          {
            second_msg.innerText = `Using first archive before ${second_date.value} — ` +
                                   archive_date_strings[reversed_dates[prev]];
            second_date.value = reversed_dates[prev];
            second_msg.classList.add('warning');
            break;
          }
          prev = d;
        }
      }
      if (second_msg.innerText === '')
      {
        second_msg.innerText = 'No matching archive available.';
        second_msg.classList.add('error');
        second_date.value = '';
      }
    }

    if (first_date.value && second_date.value)
    {
      submit_button.removeAttribute('disabled');
    }
    else
    {
      submit_button.setAttribute('disabled', 'disabled');
    }
  }

});
