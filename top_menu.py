#! /usr/local/bin/python3

from app_header import header


def top_menu(msg=''):
  """ This is the "landing page" for the app.
  """
  header_str = header(title='CUNY Transfer Explorer Lab')

  return f"""
{header_str}
<!--
<details>
  <summary>Introduction</summary>
  <hr>
  <p>
    In order to obtain a college degree, a student must complete a certain number of course
    credits and must satisfy the requirements specified for an academic program at the college
    that awards the degree. For example, to earn a bachelor’s degree at a CUNY college, students
    must complete 120 credits of coursework, must satisfy a set of University-wide General
    Education course requirements known as “Pathways,” and must complete a set of course
    requirements for a college-specific “major,” such as psychology, mathematics, or English.
  </p>
  <p>
    When a student transfers from one college to another, the coursework they have already
    completed <em>should</em> apply seamlessly to the degree requirements at their destination
    college. Making the transfer process work smoothly across a university with 20 colleges and a
    quarter million students is a major challenge; one that CUNY addresses in many ways. At a high
    level, these may be grouped as <em>university policies</em>, <em>course mappings</em>, and
    <em>articulation agreements</em>.
  </p>
  <dl id="mechanisms-list">

    <dt>University Policies</dt>
    <dd>
      Examples of CUNY policies include uniform credit requirements for degrees (120 for
      bachelor’s; 30 for associate’s); guaranteed transferability of all credits earned at any
      CUNY college; guaranteed transfer across campuses of all Pathways requirements satisfied
      at any campus; and transferability of SUNY General Education requirements to CUNY.
    </dd>

    <dt>Course Mappings</dt>
    <dd>
      CUNYfirst (the name of the Student Information System (SIS) used by all CUNY colleges) has
      over a million<sup>&dagger;</sup> <em>transfer rules</em> that tell how courses at any CUNY
      college map onto courses at any other college.
    </dd>

    <dt>Articulation Agreements</dt>
    <dd>
      An articulation agreement is a document that helps students make the best choices among the
      possible courses they might take to satisfy program requirements at one college before
      transferring to another college. Articulation agreements typically list the course transfer
      rules that will apply when the student transfers, and often contain additional guidance to
      help students plan for an efficient transfer experience.
    </dd>

  </dl>
  <p>
   This website is used to explore the transfer rules in CUNYfirst in manageable chunks. Faculty
   and administrators can use it to see what rules are missing or need to be changed. Students can
   use it to explore what will happen to their course credits when they transfer and/or need to
   take courses at another campus to satisfy a requirement at their home campus.
  </p>
  <h2>A Note on “Blanket Credits”</h2>
  <p>
    Some courses do not have an equivalent course at the receiving college. In those cases, the
    credits will transfer as “blanket credits,” which will count towards the number needed for a
    degree, but are unlikely to satisfy any other requirements, such as part of a major.
  </p>
</details>
-->
<div class="instructions">
<h1>Welcome to “T-Rex Labs”</h1>
<p>
  This is a development and prototyping site for the CUNY Transfer Explorer (T-Rex) project. While
  everything here works (<a href="mailto:cvickery@qc.cuny.edu?subject='Transfer App issue'">let me
  know</a> if not), not everything here is actually implemented in T-Rex, and T-Rex has many
  transfer-related features that are not available here.
</p>
<p>
  Feel free to browse what’s available here. Most, but not all, of the code behind this site is
  publicly available on <a href="https://github.com/cvickery">GitHub</a> if you are interested.
</p>
<p>
  But for a more polished experience, and for the many features not available here, head over to the
  <a href="https://explorer.cuny.edu">CUNY Transfer Explorer</a> site.
</div>

<div id="menu">
  <h1>Menu</h1><hr>
  <dl id="menu-list">

    <dt><a href="/search_programs">Search Programs</a></dt>
    <dd>
      Development tool for looking up academic programs based on CIP Codes and CIP-SOC mappings.
    </dd>

    <dt><a href="/describe_programs">Program Descriptions</a></dt>
    <dd>
      Development tool for cross-checking T-Rex: Describes Majors and Minors, based on Degree Works
      information about them.
    </dd>

    <dt><a href="/what_requirements">What Requirements Can a Course Satisfy?</a></dt>
    <dd>
      <p>
        <em>Enter a course_id or a tuple &ltinstitution discipline catalog_number&gt; and see
        information about what requirements the course satisfies at the college that offers it.
        Information includes the IDs of the Scribe blocks as well as the names of the requirements,
        and certain conditions that might affect the course’s applicability.</em>
      </p>
      <p>Sample input:</p>
      <ul>
        <li>qns csci 111</li>
        <li>12345</li>
      </ul>
      <p>
        This is a development tool, used to use to verify that T-Rex and this site both “understand”
        program requirements the same way.
      </p>
    </dd>

    <dt><a href="/requirements">Degree and Program Requirements</a></dt>
    <dd>
      <p>
        This feature lets you look at the Ellucian Degree Works Scribe language code for all the
        Majors, Minors, Concentrations, and Degrees offered at CUNY. Each block of code is also
        shown in an expanded form that shows exactly what courses satisfy each requirement specified
        in the block. Courses are shown as listed in the Scribe code block, as well as their status
        in CUNYfirst: active, inactive, or not present.
      </p>
    </dd>

    <dt><a href="/registered_programs">Academic Programs</a></dt>
    <dd>
      <p>
        Tabular information about all academic programs registered with the NYS Department of
        Education for all CUNY colleges. Includes information about program “variants,” such as
        programs that are shared across colleges and/or programs that can award multiple degrees
        or certificates.
      </p>
      <p>
        This information is obtained by code that “<a
        href="https://en.wikipedia.org/wiki/Web_scraping">scrapes</a>” the NYS Department of
        Education <a href="http://www.nysed.gov/heds/irpsl1.html">website</a> where all academic
        programs in the state are listed. The NYSED site is very useful, but tedious to interact
        with manually.
      </p>
      <p>
        The tables include links to the previous item’s requirement pages for each program.
      </p>
    </dd>


    <dt><a href="/map_courses">Course Transfer Maps</a></dt>
    <dd>
     <p>
      Find out how courses transfer across CUNY colleges. Results are presented in tabular form with
      cells highlighted to identify possible problems with the transfer rules.
     </p>
    </dd>
    <dt><a href="/review_rules">Review Transfer Rules</a></dt>
    <dd>
      Review details about, and optionally make suggestions for changing, existing transfer rules.
    </dd>

    <dt><a href="/rule_changes">Rule Changes</a></dt>
    <dd>
      <p>
        See what transfer rules have changed between two dates.
      </p>
    </dd>

    <dt><a href="/pending">Pending Reviews</a></dt>
    <dd>
      This is a maintenance utility that shows transfer rule suggestions that have been submitted
      but for which the user has not yet responded to an “activation” email message.
    </dd>

    <dt><a href="/courses">College Course Catalogs</a></dt>
    <dd>
      Display a complete list of all the active courses for any CUNY College in standard
      college-bulletin format. But you have to say “Please,” and then be prepared for a “firehose”
      stream of information about thousands of courses. The flood of output has been known to drown
      some mobile browsers!
      <p>
        When looking at transfer rules, you will see these catalog descriptions for just those
        courses involved in a rule.
      </p>
    </dd>

  </dl>

</div>
  <h2>Problems?</h2>
  <em>
    Please report any issues with this site to <a
    href="mailto:cvickery@qc.cuny.edu?subject='Transfer App issue'">Christopher Vickery</a>.
  </em>
  <!-- Messages -->
  <hr>
  {msg}
  """
