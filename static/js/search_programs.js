/* Manage the search-for-programs events.
 */

// Module-level variables initialized by load event handler, used by other event handlers and by
// search_programs()
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

/*  search_programs()
 *  -----------------------------------------------------------------------------------------------
 *
 *  When an input event occurs, this function is used to send the current set of input values in the
 *  DOM to the server for processing, and to receive a response providing information for updating
 *  the view.
 */
async function search_programs(search_request)
{
  // Create the search object and send it to the server's "AJAX" view for processing
  const request_obj = {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(search_request),
    };
  const response = await fetch('/_search_programs/', request_obj)
      // Wait for the response
      .then((response) => {
        if (!response.ok) {
          return JSON.stringify({error: 'Response not ok'}); // Awkward error handler
        }
        else {
          return response.json();
        }
      })
      // Use the JSON-ified response to update the DOM
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
          // Debugging: errors should not occur!
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

//  Load event handler
//  -----------------------------------------------------------------------------------------------
window.addEventListener('load', function() {

/* Locate DOM Elements
 *  -----------------------------------------------------------------------------------------------
 */
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

  /*  Heuristic slider management
   *  ---------------------------------------------------------------------------------------------
   */
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

  /*  Text input management
   *  ---------------------------------------------------------------------------------------------
   */
  search_text_element.focus();
  // TODO: provide a mechanism to pick whether to respond to keyup or change events when the page
  // first loads.
//  const event_type = 'change';
  const event_type = 'keyup';
  search_text_element.addEventListener(event_type, function(e)
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

