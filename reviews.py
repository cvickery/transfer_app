"""
Functions for creating review events, updating rule statuses, and generating associated
reports. Or maybe just for converting pending reviews to events and statuses.
"""

import json

import psycopg
from psycopg.rows import namedtuple_row
from reviews_status_utils import abbr_to_bitmask, status_string
from collections import namedtuple

RuleKey = namedtuple(
    "RuleKey",
    """ source_institution
                                    destination_institution
                                    subject_area
                                    group_number
                                """,
)


def process_pending(row):
    """Look up the token and generate events. Return as status message."""
    token = row.token
    reviews = json.loads(row.reviews)
    email = row.email
    when_entered = row.when_entered
    summaries = ""

    with psycopg.connect("dbname=cuny_curriculum") as conn:
        with conn.cursor(row_factory=namedtuple_row) as cursor:
            institutions = set()
            for review in reviews:
                key = RuleKey._make(review["rule_key"].split(":"))
                institutions.add(key.source_institution)
                institutions.add(key.destination_institution)
                cursor.execute(
                    """
          select id, review_status
            from transfer_rules
          where source_institution = %s
            and destination_institution = %s
            and subject_area = %s
            and group_number = %s
          """,
                    key,
                )
                rule_id, old_status = cursor.fetchone()
                # Generate an event for this review
                q = """
        insert into events (rule_id, event_type,
                            who, what, event_time)
                          values (%s, %s, %s, %s, %s)"""
                cursor.execute(
                    q, (rule_id, review["event_type"], email, review["comment_text"], when_entered)
                )

                # Update the review state for this rule.
                new_status = old_status | abbr_to_bitmask[review["event_type"]]
                q = "update transfer_rules set review_status = %s where id = %s"
                cursor.execute(q, (new_status, rule_id))

                # Generate a summary of this review
                new_status_str = status_string(new_status)
                # Convert to event-history link for the rule
                new_status_str = f"""
        <a href="/history/{review["rule_key"]}"
          target="_blank"
          rel="noopener noreferrer">{new_status_str}</a>"""
                summaries += f"""
        <tr>
          {review["rule_str"]}
        </tr>
        """

            # Remove record from pending_reviews
            cursor.execute("delete from pending_reviews where token = %s", (token,))

    suffix = "s"
    have_has = "were"
    num_reviews = len(reviews)
    if num_reviews == 1:
        suffix = ""
        have_has = "was"
    if num_reviews < 13:
        num_reviews = [
            "",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
        ][num_reviews - 1]

    # Return summary as an html table, and the set of institutions affected.
    return (
        f"""
  <p class="instructions">
    The following {num_reviews} transfer rule review{suffix} {have_has} submitted by
    <em>{email}</em> on {when_entered.strftime("%B %d, %Y at %I:%M %p")}.
  </p>
  <table>
    <tr>
      <th colspan="5">Rule</th>
      <th>Previous Review Status<br/><em>(links show review history)</em></th>
      <th colspan="2">New Review Status</th>
    </tr>
    {summaries}
  </table>
    """,
        institutions,
    )
