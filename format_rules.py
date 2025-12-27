#! /usr/bin/env python3

import argparse
from collections import namedtuple
import os
import psycopg
import re
import sys

from psycopg.rows import namedtuple_row
from flask import session
from reviews_status_utils import status_string

DEBUG = os.getenv("DEVELOPMENT")
DEBUG = False

Work_Tuple = namedtuple("Work_Tuple", "course_id offer_nbr discipline")

# Named tuples for a transfer rule and its source and destination course lists.
Transfer_Rule = namedtuple(
    "Transfer_Rule",
    """
                           rule_id
                           source_institution
                           destination_institution
                           subject_area
                           group_number
                           source_disciplines
                           source_subjects
                           review_status
                           source_courses
                           destination_courses
                           """,
)

# The information from the source and destination courses tables is augmented with a count of how
# many offer_nbr values there are for the course_id.
Source_Course = namedtuple(
    "Source_Course",
    """
                           course_id
                           offer_nbr
                           offer_count
                           discipline
                           catalog_number
                           discipline_name
                           cuny_subject
                           cat_num
                           min_credits
                           max_credits
                           min_gpa
                           max_gpa
                           """,
)

Destination_Course = namedtuple(
    "Destination_Course",
    """
                                course_id
                                offer_nbr
                                offer_count
                                discipline
                                catalog_number
                                discipline_name
                                cuny_subject
                                cat_num
                                transfer_credits
                                credit_source
                                is_mesg
                                is_bkcr
                                """,
)

conn = psycopg.connect("dbname=cuny_curriculum")
cursor = conn.cursor(row_factory=namedtuple_row)
cursor.execute("select code, prompt from cuny_institutions order by lower(name)")
institution_names = {row.code: row.prompt for row in cursor}
cursor.close


# andor_list()
# -------------------------------------------------------------------------------------------------
def andor_list(items, andor="and"):
    """Join a list of stings into a comma-separated con/disjunction.
    Forms:
      a             a
      a and b       a or b
      a, b, and c   a, b, or c
    """
    return_str = ", ".join(items)
    k = return_str.rfind(",")
    if k > 0:
        k += 1
        return_str = return_str[:k] + f" {andor}" + return_str[k:]
    if return_str.count(",") == 1:
        return_str = return_str.replace(",", "")
    return return_str


# _grade()
# -------------------------------------------------------------------------------------------------
def _grade(min_gpa, max_gpa):
    """Convert numerical gpa range to description of required grade in letter-grade form.
    The issue is that gpa values are not represented uniformly across campuses, and the strings
    used have to be floating point values, which lead to imprecise boundaries between letter
    names.
    """

    # Convert GPA values to letter grades by table lookup.
    # int(round(3×GPA)) gives the index into the letters table.
    # Index positions 0 and 1 aren't actually used.
    """
          GPA  3×GPA  Index  Letter
          4.3   12.9     13      A+
          4.0   12.0     12      A
          3.7   11.1     11      A-
          3.3    9.9     10      B+
          3.0    9.0      9      B
          2.7    8.1      8      B-
          2.3    6.9      7      C+
          2.0    6.0      6      C
          1.7    5.1      5      C-
          1.3    3.9      4      D+
          1.0    3.0      3      D
          0.7    2.1      2      D-
    """
    letters = ["F", "F", "D-", "D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]

    assert min_gpa <= max_gpa, f"{min_gpa=} greater than {max_gpa=}"

    # Put gpa values into “canonical form” to deal with creative values found in CUNYfirst.

    # Courses transfer only if the student passed the course, so force the min acceptable grade
    # to be a passing (D-) grade.
    if min_gpa < 1.0:
        min_gpa = 0.7
    # Lots of values greater than 4.0 have been used to mean "no upper limit."
    if max_gpa > 4.0:
        max_gpa = 4.0

    # Generate the letter grade requirement string

    if min_gpa < 1.0 and max_gpa > 3.7:
        return "Pass"

    if min_gpa >= 0.7 and max_gpa >= 3.7:
        letter = letters[int(round(min_gpa * 3))]
        return f"{letter} or above"

    if min_gpa > 0.7 and max_gpa < 3.7:
        return f"Between {letters[int(round(min_gpa * 3))]} and {letters[int(round(max_gpa * 3))]}"

    if max_gpa < 3.7:
        letter = letters[int(round(max_gpa * 3))]
        return "Below " + letter

    return "Pass"


# format_rules()
# -------------------------------------------------------------------------------------------------
def format_rules(rules, scrollable=False):
    """Generate HTML table with information about each transfer rule."""

    # Sort the rules by discipline-cat-num of first source_course
    #   First, order by decreasing stringency of GPA requiements
    rules.sort(
        key=lambda r: (r.source_courses[0].min_gpa, r.source_courses[0].max_gpa), reverse=True
    )
    #   Then, order by increasing discipline-cat_num
    rules.sort(key=lambda r: (r.source_courses[0].discipline, r.source_courses[0].cat_num))

    # Generate the table
    if scrollable:
        class_attribute = ' class="scrollable"'
    else:
        class_attribute = ""
    table = f"""
    <table id="rules-table"{class_attribute}>
      <thead>
        <tr>
          <th>Sending</th>
          <th>Courses</th>
          <th>Credits</th>
          <th>Receiving</th>
          <th>Courses</th><th>Review Status</th>
        </tr>
      </thead>
      <tbody>
      """
    for rule in rules:
        row, description = format_rule(rule)
        table += row
    table += "</tbody></table>"
    return table


# format_rule_by_key()
# -------------------------------------------------------------------------------------------------
def format_rule_by_key(rule_key):
    """Generate a Transfer_Rule tuple given the key."""
    if DEBUG:
        print(f"format_rule_by_key({rule_key})", file=sys.stderr)

    conn = psycopg.connect("dbname=cuny_curriculum")
    cursor = conn.cursor(row_factory=namedtuple_row)

    cursor.execute(
        """
  select * from transfer_rules
   where source_institution = %s
     and destination_institution = %s
     and subject_area = %s
     and group_number = %s
  """,
        rule_key.split(":"),
    )

    rule = cursor.fetchone()
    """
      Source_Course
        course_id
        offer_count
        discipline
        catalog_number
        discipline_name
        cuny_subject
        cat_num
        min_credits
        max_credits
        min_gpa
        max_gpa

      Destination_Course
        course_id
        offer_count
        discipline
        catalog_number
        discipline_name
        cuny_subject
        cat_num
        transfer_credits
        credit_source
        is_mesg
        is_bkcr
  """
    cursor.execute(
        """
    select  sc.course_id,
            sc.offer_nbr,
            sc.offer_count,
            sc.discipline,
            sc.catalog_number,
            dn.discipline_name,
            sc.cuny_subject,
            sc.cat_num,
            sc.min_credits,
            sc.max_credits,
            sc.min_gpa,
            sc.max_gpa
    from source_courses sc, cuny_disciplines dn
    where sc.rule_id = %s
      and dn.institution = %s
      and dn.discipline = sc.discipline
    order by discipline, cat_num
    """,
        (rule.id, rule.source_institution),
    )
    source_courses = [Source_Course._make(c) for c in cursor.fetchall()]

    cursor.execute(
        """
    select  dc.course_id,
            dc.offer_nbr,
            dc.offer_count,
            dc.discipline,
            dc.catalog_number,
            dn.discipline_name,
            dc.cuny_subject,
            dc.cat_num,
            dc.transfer_credits,
            dc.credit_source,
            dc.is_mesg,
            dc.is_bkcr
     from destination_courses dc, cuny_disciplines dn
    where dc.rule_id = %s
      and dn.institution = %s
      and dn.discipline = dc.discipline
    order by discipline, cat_num
    """,
        (rule.id, rule.destination_institution),
    )
    # 'offer_count', 'discipline', 'catalog_number', 'discipline_name', 'cuny_subject', 'cat_num',
    # 'transfer_credits', 'credit_source', 'is_mesg', and 'is_bkcr'
    destination_courses = [Destination_Course._make(c) for c in cursor.fetchall()]

    the_rule = Transfer_Rule._make(
        [
            rule.id,
            rule.source_institution,
            rule.destination_institution,
            rule.subject_area,
            rule.group_number,
            rule.source_disciplines,
            rule.source_subjects,
            rule.review_status,
            source_courses,
            destination_courses,
        ]
    )

    conn.close()
    return format_rule(the_rule, rule_key)


# format_rule()
# -------------------------------------------------------------------------------------------------
def format_rule(rule, rule_key=None):
    """Return two strings, one that represents the rule as a table row and one that is a HTML
    paragraph.
    """
    if rule_key is None:
        rule_key = "{}:{}:{}:{}".format(
            rule.source_institution,
            rule.destination_institution,
            rule.subject_area,
            rule.group_number,
        )

    # In case there are cross-listed courses to look up
    conn = psycopg.connect("dbname=cuny_curriculum")
    cursor = conn.cursor(row_factory=namedtuple_row)

    # Extract disciplines and courses from the rule
    source_courses = rule.source_courses
    destination_courses = rule.destination_courses

    # Check validity of Source and Destination course_ids
    source_course_ids = [course.course_id for course in rule.source_courses]
    # There should be no duplicates in source_course_ids for the rule
    # assert len(set(source_course_ids)) == len(source_course_ids), \
    #     f'Duplcated source course id(s) for rule {rule_key}'
    source_course_id_str = ":".join([f"{id}" for id in source_course_ids])

    destination_course_ids = [course.course_id for course in rule.destination_courses]
    # There should be no duplicates in destination_course_ids for the rule
    assert len(set(destination_course_ids)) == len(destination_course_ids), (
        f"Duplcated destination course id(s) for rule {rule_key}"
    )
    destination_course_id_str = ":".join([f"{id}" for id in destination_course_ids])
    #  Check for any cross-listed source courses. Look up their disciplines and catalog_numbers.
    cross_listed_with = dict()
    for course in source_courses:
        if course.offer_count > 1:
            cursor.execute(
                """select discipline, catalog_number, cuny_subject
                          from cuny_courses
                         where course_id = %s""",
                (course.course_id,),
            )
            assert cursor.rowcount == course.offer_count, (
                "cross-listed source course counts do not match"
            )
            cross_listed_with[course.course_id] = cursor.fetchall()
    cursor.close()

    # The course ids parts of the table row id
    row_id = "{}|{}|{}".format(rule_key, source_course_id_str, destination_course_id_str)
    min_source_credits = 0.0
    max_source_credits = 0.0
    source_course_list = ""

    # Assumptions and Presumptions:
    # - All source courses do not necessarily have the same discipline.
    # - Grade requirement can chage as the list of courses is traversed.
    # - If course has cross-listings, list cross-listed course(s) in parens following the
    #   catalog number. AND-list within a list of courses having the same grade requirement. OR-list
    #   for cross-listed courses.
    # Examples:
    #   Passing grades in LCD 101 (=ANTH 101 or CMLIT 207) and LCD 102.
    #   Passing grades in LCD 101 (=ANTH 101) and LCD 102. C- or better in LCD 103.

    # First, group courses by grade requirement. Not sure there will ever be a mix for one rule, but
    # if it ever happens, we’ll be ready.
    courses_by_grade = dict()
    for course in source_courses:
        # Accumulate min/max credits for checking against destination credits
        min_source_credits += float(course.min_credits)
        max_source_credits += float(course.max_credits)
        if (course.min_gpa, course.max_gpa) not in courses_by_grade.keys():
            courses_by_grade[(course.min_gpa, course.max_gpa)] = []
        courses_by_grade[(course.min_gpa, course.max_gpa)].append(course)

    # For each grade requirement, sort by cat_num, and generate array of strings to AND-list
    # together.
    by_grade_keys = [key for key in courses_by_grade.keys()]
    by_grade_keys.sort()

    for key in by_grade_keys:
        grade_str = _grade(key[0], key[1])
        if grade_str != "Pass":
            grade_str += " in "
        courses = courses_by_grade[key]
        courses.sort(key=lambda c: c.cat_num)
        course_list = []
        for course in courses:
            course_str = f"{course.discipline} {course.catalog_number}"
            if course.course_id in cross_listed_with.keys():
                xlist_courses = []
                for xlist_course in cross_listed_with[course.course_id]:
                    if (
                        xlist_course.discipline != course.discipline
                        or xlist_course.catalog_number != course.catalog_number
                    ):
                        xlist_courses.append(
                            f"{xlist_course.discipline} {xlist_course.catalog_number}"
                        )
                course_str += "(=" + andor_list(xlist_courses, "or") + ")"
            course_list.append(f'<span title="course_id={course.course_id}">{course_str}</span>')
        source_course_list += f"{grade_str} {andor_list(course_list, 'and')}"

    # Build the destination part of the rule group
    #   If any of the destination courses has the BKCR attribute, the credits for that course will
    #   be  whatever is needed to make the credits match the sum of the sending course credits.
    destination_credits = 0.0
    has_bkcr = False
    discipline = ""
    destination_course_list = ""
    for course in destination_courses:
        if course.is_bkcr:
            has_bkcr = True  # Number of credits will be computed to match source credits
            cat_num_class = ' class="blanket"'
        else:
            destination_credits += float(course.transfer_credits)
            cat_num_class = ""
        course_catalog_number = course.catalog_number
        if discipline != course.discipline:
            if destination_course_list != "":
                destination_course_list = destination_course_list.strip("/") + "; "
            discipline_str = f'<span title="{course.discipline_name}">{course.discipline}</span>'
            destination_course_list = destination_course_list.strip("/ ") + discipline_str + "-"

        destination_course_list += (
            f'<span title="course id: {course.course_id}"{cat_num_class}>'
            f"{course_catalog_number}</span>/"
        )

    destination_course_list = destination_course_list.strip("/").replace(";", " and ")

    row_class = "rule"

    # Credits match if there is BKCR, otherwise, check if in range.
    if destination_credits < min_source_credits and has_bkcr:
        destination_credits = min_source_credits
    elif destination_credits < min_source_credits or destination_credits > max_source_credits:
        row_class += " credit-mismatch"

    if min_source_credits != max_source_credits:
        source_credits_str = f"{min_source_credits}-{max_source_credits}"
    else:
        source_credits_str = f"{min_source_credits}"

    # If the rule has been evaluated, the last column is a link to the review history. But if it
    # hasn’t been evaluated yet, the last column is just the text that says so.
    status_cell = status_string(rule.review_status)
    if rule.review_status != 0:
        status_cell = f"""<a href="{session["base_url"]}history/{rule_key}">{status_cell}</a>"""
    status_cell = '<span title="{}">{}</span>'.format(rule_key, status_cell)
    row = """<tr id="{}" class="{}">
              <td title="{}">{}</td>
              <td>{}</td>
              <td>{}</td>
              <td title="{}">{}</td>
              <td>{}</td>
              <td>{}</td>
            </tr>""".format(
        row_id,
        row_class,
        institution_names[rule.source_institution],
        rule.source_institution.rstrip("0123456789"),
        source_course_list,
        f"{source_credits_str} => {destination_credits}",
        institution_names[rule.destination_institution],
        rule.destination_institution.rstrip("0123456789"),
        destination_course_list,
        status_cell,
    )
    description = f"""<span class="{row_class} description">{source_course_list}
        at {institution_names[rule.source_institution]},
        {source_credits_str} credits, transfers to
        {institution_names[rule.destination_institution]}
        as {destination_course_list}, {destination_credits} credits.</span>"""
    description = description.replace("Pass", "Passing grade in")

    return row, description


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Testing transfer rules")
    parser.add_argument("--debug", "-d", action="store_true", default=False)
    parser.add_argument("--grade", "-g", nargs=2)
    parser.add_argument("--rule", "-r")
    args = parser.parse_args()

    if args.debug:
        DEBUG = True
    if args.grade:
        min_gpa = float(args.grade[0])
        max_gpa = float(args.grade[1])
        print(f'"{_grade(min_gpa, max_gpa)}"')
    if args.rule:
        html, description = format_rule_by_key(args.rule)
        description = re.sub(r"\s+", " ", re.sub("<.*?>", "", description).replace("\n", " "))
        print(f"{args.rule}\n{description}")
