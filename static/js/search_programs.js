/* Monitor the search-by-cip form events.
 */

let search_text_element = null;
let heuristic_element = null;
let heuristic_value_span = null;
let coarse_cip_count = null;
let medium_cip_count = null;
let fine_cip_count = null;
let coarse_cip_codes = null;
let medium_cip_codes = null;
let fine_cip_codes = null;
let coarse_plan_count = null;
let medium_plan_count = null;
let fine_plan_count = null;
let plans_list = null;

async function search_programs(search_request)
{
  const request_obj = {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(search_request),
    };
  const response = await fetch('/_search_programs/', request_obj)
      .then((response) => {
        if (!response.ok) {
          return JSON.stringify({error: 'Response not ok'}); // Ignore errors
        }
        else {
          return response.json();
        }
      })
      .then((search_result) => {
        try
        {
          const coarse_cips = search_result['coarse']['cip_codes'];
          let num_matches = coarse_cips.length;
          if (num_matches == 1) {text = 'CIP Code'} else { text = 'CIP Codes'}
          coarse_cip_count.innerHTML = `${num_matches} ${text}`;
          let inner_html = '';
          for (let i = 0; i < coarse_cips.length; i++)
          {
            inner_html += `<div>${coarse_cips[i]}</div>`;
          }
          coarse_cip_codes.innerHTML = inner_html;

          const medium_cips = search_result['medium']['cip_codes'];
          num_matches = medium_cips.length;
          if (num_matches == 1) {text = 'CIP Code'} else {text = 'CIP Codes'}
          medium_cip_count.innerHTML = `${num_matches} ${text}`;

          inner_html = ''
          for (let i = 0; i < medium_cips.length; i++)
          {
            inner_html += `<div>${medium_cips[i]}</div>`;
          }
          medium_cip_codes.innerHTML = inner_html;

          matches = search_result['fine']['cip_codes'].length;
          if (matches == 1) {text = 'CIP Code'} else { text = 'CIP Codes'}
          fine_cip_count.innerHTML = `${matches} ${text}`;

          inner_html = ''
          cip_codes = search_result['fine']['cip_codes'];
          for (let i = 0; i < cip_codes.length; i++)
          {
            inner_html += `<div>${cip_codes[i]}</div>`;
          }
          fine_cip_codes.innerHTML = inner_html;

          coarse_plan_count.innerHTML = search_result['coarse']['plans'].length;
          medium_plan_count.innerHTML = search_result['medium']['plans'].length;
          fine_plan_count.innerHTML = search_result['fine']['plans'].length;
          for (const detail_level of ['coarse', 'medium', 'fine'])
          {
            let inner_html = '';
            // The plans are in sub-lists, grouped by CIP
            for (const plan_item of search_result[detail_level]['plans'])
            {
              [institution, plan, enrollment, title] = plan_item;
              inner_html += `<div class="list-item">
                               <strong>${title}</strong><br>
                               ${institution} ${plan} <span class="enroll">${enrollment}</span>
                             </div>`
            }
            plans_list[detail_level].innerHTML = inner_html;
          }
        }
        catch (error)
        {
          console.log(error);
          coarse_cip_count.innerHTML = `No CIP Codes`;
          medium_cip_count.innerHTML = `No CIP Codes`;
          fine_cip_count.innerHTML = `No CIP Codes`;
          coarse_plan_count.innerHTML = 'Zero';
          medium_plan_count.innerHTML = 'Zero';
          fine_plan_count.innerHTML = 'Zero';
          for (const detail_level of ['coarse', 'medium', 'fine'])
          {
            plans_list[detail_level].innerHTML = ''
          }
        }
      });
}

window.addEventListener('load', function() {

  search_text_element = document.getElementById('search_text');
  heuristic_element = document.getElementById('heuristic');
  heuristic_value_span = document.getElementById('heuristic-value');

  coarse_cip_count = document.getElementById('num-coarse-cip');
  medium_cip_count = document.getElementById('num-medium-cip');
  fine_cip_count = document.getElementById('num-fine-cip');

  coarse_cip_codes = document.getElementById('coarse-cip-codes');
  medium_cip_codes = document.getElementById('medium-cip-codes');
  fine_cip_codes = document.getElementById('fine-cip-codes');

  coarse_plan_count = document.getElementById('num-coarse-plan');
  medium_plan_count = document.getElementById('num-medium-plan');
  fine_plan_count = document.getElementById('num-fine-plan');

  plans_list = {
    'coarse': document.getElementById('coarse-plans'),
    'medium': document.getElementById('medium-plans'),
    'fine': document.getElementById('fine-plans'),
  }

  let enough = (heuristic_element.value / 100.0);
  heuristic_value_span.innerHTML = ` (${heuristic_element.value}%)`

  heuristic_element.addEventListener('change', function(e)
  {
    // Convert integer 0-100 to percentage for display, and update the “enough” heuristic value
    heuristic_value_span.innerHTML = ` (${heuristic_element.value}%)`
    enough = heuristic_element.value / 100.0;
    let search_request = {search_text: search_text_element.value,
                          enough: enough,
                          colleges: [],
                          plans: true,
                          subplans: true}

    search_programs(search_request);
  });

  search_text_element.focus();
  search_text_element.addEventListener('change', function(e)
  {
    // Create the query string based on element settings
    let search_request = {search_text: search_text_element.value,
                          enough: enough,
                          colleges: [],
                          plans: true,
                          subplans: true}

    search_programs(search_request);
  });
});

