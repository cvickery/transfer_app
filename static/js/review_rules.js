/* This script handles all 3+ steps of the transfer review application.
 * as such, it should probably be broken up into separate scripts to avoid cross-step code
 * pollution. One reason it works is that there are no consequences for hooking code to elements
 * that don't actually exist in a particular step's DOM.
 * For now it continues its monolithic megopoly.
 */

$(function ()
{
  $('#need-js').hide();
  $('#review-form').hide();

  // Global action: escape key hides dialogs, currently only the review-panel in form 2.
  $('*').keyup(function (event)
  {
    if (event.keyCode === 27)
    {
      $('.rule').removeClass('selected-rule');
      $('#review-form').hide();
    }
  });

  var error_msg = '';
  var dismiss_bar = '<div id="dismiss-bar" class="dismiss">×</div>';
  var pending_reviews = [];

  // Form #1 Select Colleges
  // ==============================================================================================
  /* Presented with a lists of all institutions, user has to select one sender and 1+ receivers or
   * vice-versa. Must supply a valid CUNY email address.
   */
  $('#submit-form-1').prop('disabled', true).css('color', '#cccccc');

  $('#all-sources, #all-destinations').prop('disabled', false);
  $('#no-sources, #no-destinations').prop('disabled', false);
  var ok_to_submit_1 = error_msg === '';

  // validate_form_1()
  // ----------------------------------------------------------------------------------------------
  function validate_form_1()
  {
    error_msg = '';
    var num_source = $('.source:checked').length;
    var num_dest = $('.destination:checked').length;
    var valid_email = /^\s*\w+(.\w+)*@(\w+\.)*cuny.edu\s*$/i.test($('#email-text').val());

    //  Check number of institutions selected
    if ((num_source === 1 && num_dest > 0) ||
        (num_source > 0 && num_dest === 1))
    {
      error_msg = '';
    }
    else
    {
      error_msg += '<p>You must select either a single sending college and one or more ' +
                   'receiving colleges or a single receiving college and one or more ' +
                   'sending colleges.</p>';
    }

    //  Check CUNY email address
    /*  It's an error if value is not blank, otherwise it's a warning. But in either case, the
     *  form can't be submitted yet.
     */
    bg_color = '#ffffff';
    if (!valid_email)
    {
      if ($('#email-text').val() !== '')
      {
        // User entered an invalid email
        bg_color = '#ff9999'; // error
        if (error_msg === '')
        {
          error_msg = '<p>You must supply a valid CUNY email address.</p>';
        }
      }
      else
      {
        // No email yet
        bg_color = '#ffffcc'; // warning
        if (error_msg === '')
        {
          // Valid selections with no email: prompt for it
          error_msg = '<p>Enter your CUNY email address.</p>';
        }
      }
    }

    $('#email-text').css('background-color', bg_color);

    $('#error-msg').html(error_msg);
    ok_to_submit_1 = error_msg === '';
    if (ok_to_submit_1)
    {
      $('#submit-form-1').prop('disabled', false).css('color', '#000000');
    }
    else
    {
      $('#submit-form-1').prop('disabled', true).css('color', '#cccccc');
    }
  }

  // Form 1: Button click handlers to clear or set groups of institution checkboxes
  // ----------------------------------------------------------------------------------------------
  $('#all-sources').click(function (event)
  {
    $('.source').prop('checked', true);
    validate_form_1();
  });

  $('#no-sources').click(function (event)
  {
    $('.source').prop('checked', false);
    validate_form_1();
  });

  $('#all-destinations').click(function ()
  {
    $('.destination').prop('checked', true);
    validate_form_1();
  });

  $('#no-destinations').click(function ()
  {
    $('.destination').prop('checked', false);
    validate_form_1();
  });

  // If any checkbox or the email text changes, validate the form
  $('input').change(function ()
  {
    validate_form_1();
  });

  // Form 1: Submit the form. Maybe.
  // ----------------------------------------------------------------------------------------------
  var submit_button_1 = false;
  $('#form-1').submit(function (event)
  {
    return submit_button_1;
  });

  $('#submit-form-1').click(function (event)
  {
    submit_button_1 = true;
  });

  // Form 2 Select Disciplines
  // ==============================================================================================
  /* Given a list of sending and receiving offered disciplines, grouped by CUNY subject names, the
   * user must select at least one discipline group from the sending column and at least one from
   * the receiving column. Shortcut checkboxes let the user clear or select all items in a
   * column. The wrinkle is that the user thinks "disciplines" but the app thinks "cuny_subjects."
   */

  // Form 2: Manage checkboxes
  // ----------------------------------------------------------------------------------------------

  $('.f2-cbox').has('input').css('background-color', 'white');

  //  When shortcut checkboxes change state
  $('#all-source-subjects').change(function ()
  {
    if (this.checked)
    {
      $('.source-subject input:checkbox').prop('checked', true);
      $('#no-source-subjects').prop('checked', false);
    }
  });

  $('#no-source-subjects').change(function ()
  {
    if (this.checked)
    {
      $('.source-subject input:checkbox').prop('checked', false);
      $('#all-source-subjects').prop('checked', false);
    }
  });

  $('#all-destination-subjects').change(function ()
  {
    if (this.checked)
    {
      $('.destination-subject input:checkbox').prop('checked', true);
      $('#no-destination-subjects').prop('checked', false);
    }
  });

  $('#no-destination-subjects').change(function ()
  {
    if (this.checked)
    {
      $('.destination-subject input:checkbox').prop('checked', false);
      $('#all-destination-subjects').prop('checked', false);
    }
  });

  // When any source subject changes state, update the "all" and "no" shortcut states.
  $('.source-subject input:checkbox').change(function ()
  {
    if (this.checked)
    {
      // Source Checked
      $('#no-source-subjects').prop('checked', false);
      let all_checked = true;
      $('.source-subject input:checkbox').each(function ()
      {
        if (!this.checked)
        {
          all_checked = false;
          return false;
        }
      });
      $('#all-source-subjects').prop('checked', all_checked);
    }
    else
    {
      // Unchecked
      $('#all-source-subjects').prop('checked', false);
      // If there are none selected now, check the "none" shortcut box
      let all_unchecked = true;
      $('.source-subject input:checkbox').each(function ()
      {
        if (this.checked)
        {
          all_unchecked = false;
          return false;
        }
      });
      $('#no-source-subject').prop('checked', all_unchecked);
    }
  });

  // When any destination subject changes state, update the "all" and "no" shortcut states.
  $('.destination-subject input:checkbox').change(function ()
  {
    if (this.checked)
    {
      // Source Checked
      $('#no-destination-subjects').prop('checked', false);
      let all_checked = true;
      $('.destination-subject input:checkbox').each(function ()
      {
        if (!this.checked)
        {
          all_checked = false;
          return false;
        }
      });
      $('#all-destination-subjects').prop('checked', all_checked);
    }
    else
    {
      // Unchecked
      $('#all-destination-subjects').prop('checked', false);
      // If there are none selected now, check the "none" shortcut box
      let all_unchecked = true;
      $('.destination-subject input:checkbox').each(function ()
      {
        if (this.checked)
        {
          all_unchecked = false;
          return false;
        }
      });
      $('#no-destination-subjects').prop('checked', all_unchecked);
    }
  });

  $('#form-2').submit(function ()
  {
    $('#form-2').css('cursor', 'wait');
  });

  //  Form 2: Hide instructions
  // ----------------------------------------------------------------------------------------------
  $('.instructions').click(function ()
  {
    var this_height = $(this).height();
    $(this).hide();
    $('.selection-table-div').height($('.selection-table-div').height() + this_height);
  });



  //  Form 3 Validation and Processing
  //  =============================================================================================
  /*  Clicking on a rule in the rules table brings up the review form.
   */
  $('.rule').click(function (event)
  {
    // clicks in the prior reviews column do not select a rule.
    if (event.target.nodeName === 'A')
    {
      return;
    }

    $('.rule').removeClass('selected-rule');
    $(this).addClass('selected-rule');
    var rule_str = '';
    $(this).find('td').each(function (index)
    {
      rule_str += $(this).text() + ' ';
    });

    //     Row IDs: source_institution; hyphen;
    //              destination_institution; hyphen;
    //              subject_area; hyphen;
    //              group_number; hyphen;
    //              colon-separated list of source course IDs; hyphen;
    //              colon-separated list of destination course IDs.
    //
    var row_id = $(this).attr('id');
    var review_row = document.getElementById(row_id);
    var review_row_class = review_row.className
                                             .replace(/selected-rule/, '')
                                             .replace(/evaluated/, '');
    var review_row_html = `<tr class="${review_row_class}">
                                 ${review_row.innerHTML.replace(/ id=".*"/, '')}
                               </tr>`;
    var review_rule_table = `<table>${review_row_html}</table>`;

    var first_parse = row_id.split('-');
    var rule_key = first_parse[0] + '-' +
                   first_parse[1] + '-' +
                   first_parse[2] + '-' +
                   first_parse[3];
    var source_institution = first_parse[0].replace(/_/g, ' ');
    var source_institution_str = source_institution.replace(/\d+/, '');
    var destination_institution = first_parse[1].replace(/_/g, ' ');
    var destination_institution_str = destination_institution.replace(/\d+/, '');
    // var discipline = first_parse[2];
    // var group_number = first_parse[3];
    var source_course_ids = first_parse[4].split(':');
    var destination_course_ids = first_parse[5].split(':');
    var source_request = $.getJSON($SCRIPT_ROOT + '/_courses', {course_ids: first_parse[4]});
    var dest_request = $.getJSON($SCRIPT_ROOT + '/_courses', {course_ids: first_parse[5]});

    var source_suffix = (source_course_ids.length !== 1) ? 's' : '';
    var source_catalog_div = `<div id="source-catalog-div">
                              <h2>
                                ${source_institution_str} Course${source_suffix}
                              </h2>
                              <div id="source-catalog-info">
                                <p>Waiting for catalog entries ...</p>
                                </div>
                            </div>`;
    var destination_suffix = (destination_course_ids.length !== 1) ? 's' : '';
    var destination_catalog_div = `<div id="destination-catalog-div">
                                  <h2>
                                    ${destination_institution_str} Course${destination_suffix}
                                  </h2>
                                  <div id="destination-catalog-info">
                                    <p>Waiting for catalog entries ...</p>
                                    </div>
                                </div>`;

    var controls = `<div id="review-controls-div" class="clean">
                    <div>
                      <input type="radio" name="reviewed" id="src-ok" value="src-ok"/>
                      <label for="src-ok">Verified by ${source_institution_str}</label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="src-not-ok" value="src-not-ok"/>
                      <label for="src-not-ok">Problem observed by ${source_institution_str}</label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="dest-ok" value="dest-ok"/>
                      <label for="dest-ok">
                        Verified by ${destination_institution_str}
                      </label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="dest-not-ok" value="dest-not-ok"/>
                      <label for="dest-not-ok">
                        Problem observed by ${destination_institution_str}
                      </label>
                    </div>
                    <div>
                      <input type="radio" name="reviewed" id="other" value="other"/>
                      <label for="other">Other</label>
                    </div>
                    <textarea id="comment-text"
                              placeholder="Explain problem or “Other” here."
                              minlength="12" />
                    <input type="hidden" name="src_institution"
                           value="${source_institution}" />
                    <input type="hidden" name="dest_institution"
                           value="${destination_institution}" />
                    <input type="hidden" name="rule-key" value="${rule_key}" />
                    <button class="ok-cancel"
                            id="review-submit"
                            type="button"
                            disabled="disabled">OK</button>
                    <button class="ok-cancel dismiss" type="button">Cancel</button>
                  </div>`;

    // Display the review form even if the catalog entries haven't loaded yet
    $('#review-form').html(dismiss_bar +
                               review_rule_table +
                               source_catalog_div +
                               destination_catalog_div +
                               controls)
                           .show()
                           .draggable();

    // Populate the source catalog entries in the review form when they arrive
    source_request.done(function (data, text_status)
    {
      var html_str = '';
      for (var i = 0; i < data.length; i++)
      {
        html_str += `${data[i].html} <hr/>`;
      }
      $('#source-catalog-info').html(html_str);
    });

    // Populate the destination catalog entries in the review form when they arrive
    dest_request.done(function (data, text_status)
    {
      var html_str = '';
      for (var i = 0; i < data.length; i++)
      {
        html_str += `${data[i].html}<hr/>`;
      }
      $('#destination-catalog-info').html(html_str);
    });

    /* The following lines would position the review form over the rules table.
     * Omitting them pushes the rules table down while the review form is active, which seems
     * fine to me.
     */
    // var review_form = document.getElementById('review-form');
    // var eval_form_rect = review_form.getBoundingClientRect();
    // review_form.style.position = 'fixed';
    // review_form.style.top = ((window.innerHeight / 2) - (eval_form_rect.height / 2)) + 'px';
    // review_form.style.left = ((window.innerWidth / 2) - (eval_form_rect.width / 2)) + 'px';

    // Click to dismiss the review form.
    $('.dismiss').click(function ()
    {
      $('.rule').removeClass('selected-rule');
      $('#review-form').hide();
    });

    // Enable form submission only if an input has changed.
    $('input').change(setup_ok_to_submit);
    $('textarea').keyup(setup_ok_to_submit);
    function setup_ok_to_submit()
    {
      var comment_len = $('#comment-text').val().length;
      var ok_to_submit = ($(this).attr('id') === 'src-ok' ||
                          $(this).attr('id') === 'dest-ok' ||
                          comment_len > 12);
      $('#review-submit').attr('disabled', !ok_to_submit);
    }

    // Add or update a review when user submits one.
    $('#review-submit').click(function (event)
    {
      var review =
      {
        event_type: $('input[name=reviewed]:checked').val(),
        source_institution: $('input[name=src_institution]').val(),
        destination_institution: $('input[name=dest_institution]').val(),
        comment_text: $('#comment-text').val().replace('\'', '’'),
        rule_key: rule_key,
        rule_str: review_row_html,
        include: true
      };

      // If there is already a review for this rule ...
      var new_review = true;
      for (var i = 0; i < pending_reviews.length; i++)
      {
        if (review.rule_key === pending_reviews[i].rule_key &&
            review.event_type === pending_reviews[i].event_type)
        {
          // ... the only thing that could be different is the comment
          pending_reviews[i].comment_text = review.comment_text;
          new_review = false;
          break;
        }
      }
      if (new_review)
      {
        pending_reviews.push(review);
      }

      $('.selected-rule').addClass('evaluated');

      // Update the reviews pending information
      var num_pending_text = '';
      switch (pending_reviews.length)
      {
        case 0:
          num_pending_text = 'You have not reviewed any transfer rules yet.';
          break;
        case 1:
          num_pending_text = 'You have reviewed one transfer rule.';
          break;
        default:
          num_pending_text = `You have reviewed ${pending_reviews.length} transfer rules.`;
      }
      $('#num-pending').text(num_pending_text);
      $('#review-form').hide();
      $('.selected-rule').removeClass('selected-rule');

      // Enable review/send-email button
      $('#send-email').attr('disabled', false);
      event.preventDefault(); // don't actually submit the form to the server.
    });
  });

    // Review and send email button click
    // --------------------------------------------------------------------------------------------
    /* Generate a form for reviewing the reviews so the user can omit items they don't
     * intend. Then submit the form to a web page that actually enters the items into the
     * pending_reviews table and sends email to the user.
     */
    $('#send-email').click(function (event)
    {
      var email_address = $('#email-address').text();
      var review_form = `
        <div id="review-form">
          <h2>Review Your Submissions</h2>
          <p>Un-check the Include button if you don’t want to submit an item.</p>
          <div id="reviews-table-div">
          <table id='reviews-table'>
            <tr>
              <th>Include?</th>
              <th>Rule</th>
              <th colspan="2">Your Review</th>
            </tr>
        `;
      review_form_rows = [];
      for (review in pending_reviews)
      {
        var rule_str = pending_reviews[review].rule_str;

        // Build a rule string that omits the previous status (i.e., the last td).
        rule_str = rule_str.replace(/\n\s*/g, '').replace(/<td(?!.*<td).*<\/td><\/tr>/, '</tr>');
        pending_reviews[review].rule_str = rule_str;
        var institution = 'Unknown';
        var go_nogo = 'Unknown';
        switch (pending_reviews[review].event_type)
        {
          case 'src-ok':
            institution = pending_reviews[review].source_institution;
            go_nogo = 'OK';
            break;
          case 'dest-ok':
            institution = pending_reviews[review].destination_institution;
            go_nogo = 'OK';
            break;
          case 'src-not-ok':
            institution = pending_reviews[review].source_institution + ': ';
            go_nogo = pending_reviews[review].comment_text;
            break;
          case 'dest-not-ok':
            institution = pending_reviews[review].destination_institution + ': ';
            go_nogo = pending_reviews[review].comment_text;
            break;
          default:
            institution = 'Other: ';
            go_nogo = pending_reviews[review].comment_text;
            break;

        }
        review_form += `<tr id="review-${review}">
                          <td>
                            <input type="checkbox"
                                   class="include-button"
                                   checked="checked"/>
                          </td>
                          <td>
                            <table>
                              <tr>
                                ${rule_str}
                              </tr>
                            </table>
                          </td>
                          <td>
                            ${institution.replace(/\d+/, '')}
                          </td>
                          <td>
                            ${go_nogo}
                          </td>
                        </tr>`;
      }

      review_form += `
          </table>
        </div>
        <div class='controls'>
          <input type="hidden" value="${email_address}" />
          <input type="hidden" name="next-function" value="do_form_3" />
          <input type="hidden" id="hidden-reviews" name="reviews" value="Not Set" />
          <button class="ok-cancel" type="submit" id="review-submit">Submit</button>
          <button class="ok-cancel dismiss" type="button">Cancel</button>
        </div>
      </div>`;

      // Re-use the review-form div for the reviews-review form
      $('#review-form').html(dismiss_bar + review_form)
                           .show()
                           .draggable();

      // When an include button is clicked
      $('.include-button').click(function (event)
      {
        var row = $(this).parent().parent();
        var index = row.attr('id').split('-')[1];
        // Is the review being omitted, or re-included?
        if ($(this).is(':checked'))
        {
          pending_reviews[index].include = true;
          row.removeClass('omitted');
          $('#review-submit').removeAttr('disabled');
        }
        else
        {
          pending_reviews[index].include = false;
          row.addClass('omitted');
          var any_included = false;
          for (var i = 0; i < pending_reviews.length; i++)
          {
            if (pending_reviews[i].include)
            {
              any_included = true;
              break;
            }
          }
          if (!any_included)
          {
            $('#review-submit').attr('disabled', 'disabled');
          }
        }
      });

      // Submit the reviews. This will invoke do_form_3(), which will sent the verification
      // email.
      $('#review-form').submit(function (event)
      {
        $('input[name="reviews"]').val(JSON.stringify(pending_reviews));
      });
      var review_form = document.getElementById('review-form');
      var eval_form_rect = review_form.getBoundingClientRect();
      review_form.style.position = 'fixed';
      review_form.style.top = ((window.innerHeight / 2) - (eval_form_rect.height / 2)) + 'px';
      review_form.style.left = ((window.innerWidth / 2) - (eval_form_rect.width / 2)) + 'px';
      $('.dismiss').click(function ()
      {
        $('#review-form').hide();
        $('.selected-rule').removeClass('selected-rule');
      });
    });
  });

