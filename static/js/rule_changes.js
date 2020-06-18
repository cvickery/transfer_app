
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
  const submit_msg = document.querySelector('#submit_button+span');
  if (submit_button)
  {
    first_date.addEventListener('change', first_changed);
    second_date.addEventListener('change', second_changed);
    submit_button.setAttribute('disabled', 'disabled');
  }

  //  first_changed()
  //  ---------------------------------------------------------------------------------------------
  /*  The first date has to be for an archive that has at least one archive following it.\
   */
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
        first_msg.innerText = 'Using earliest archive available — ' +
                              archive_date_strings[archive_dates[0]];
        first_msg.classList.add('warning');
        first_date.value = archive_dates[0];
      }
      else
      {
        // Search
        let prev = archive_dates[0];
        for (let d = 0; d < (archive_dates.length - 1); d++)
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
        first_msg.innerText = 'Using latest archive available for comparison — '+
                               archive_date_strings[archive_dates[archive_dates.length - 2]];
        first_msg.classList.add('warning');
        first_date.value = archive_dates[archive_dates.length - 2];
      }
    }
    check_dates();
  }

  //  second_changed()
  //  ---------------------------------------------------------------------------------------------
  function second_changed()
  {
    second_msg.innerText = '';
    second_msg.classList.remove('error');
    second_msg.classList.remove('warning');
    second_msg.classList.remove('good');
    const last_d = archive_dates.length -1;
    if (second_date.value)
    {
      if (second_date.value > archive_dates[last_d])
      {
        second_msg.innerText = 'Using most recent archive available — ' +
                               archive_date_strings[archive_dates[last_d]];
        second_msg.classList.add('warning');
        second_date.value = archive_dates[last_d];
      }
      else if (second_date.value < archive_dates[1])
      {
        second_msg.innerText = 'Using earliest archive available for comparison —' +
                               archive_date_strings[archive_dates[1]];
        second_msg.classList.add('warning');
        second_date.value = archive_dates[1];
      }
      else
      {
        // Search
        let prev = last_d;
        for (let d = last_d; d > 0; d--)
        {
          if (second_date.value === archive_dates[d])
          {
            second_msg.innerText = 'OK';
            second_msg.classList.add('good');
            break;
          }
          else if (second_date.value > archive_dates[d])
          {
            console.log(d, prev, last_d, archive_dates[prev], archive_date_strings);
            second_msg.innerText = `Using last archive before ${second_date.value} — ` +
                                   archive_date_strings[archive_dates[d]];
            second_date.value = archive_dates[d];
            second_msg.classList.add('warning');
            break;
          }
          // prev = d;
        }
      }
      if (second_msg.innerText === '')
      {
        second_msg.innerText = 'Using first archive available for comparison — ' +
                                archive_date_strings[archive_dates[1]];
        second_msg.classList.add('warning');
        second_date.value = archive_dates[1];
      }
    }
    check_dates();
  }

  // check_dates()
  // ----------------------------------------------------------------------------------------------
  /* Allow form to be submitted if both dates are valid and different from one another. But alert
   * the user if the dates are reversed.
   */
  function check_dates()
  {
    submit_msg.classList.remove('warning');
    submit_msg.innerText = '';
    if (first_date.value && second_date.value)
    {
      if (first_date.value === second_date.value)
      {
        submit_msg.innerText = 'Dates are the same: nothing to compare.';
        submit_msg.classList.add('warning');
        submit_button.setAttribute('disabled', 'disabled');
      }
      else
      {
        submit_button.removeAttribute('disabled');
        if (first_date.value > second_date.value)
        {
          submit_msg.innerText = 'This will work, but the dates are reversed.'
          submit_msg.classList.add('warning');
        }
      }
    }
    else
    {
      submit_button.setAttribute('disabled', 'disabled');
    }
  }

});
