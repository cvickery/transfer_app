#! /usr/local/bin/python3

from app_header import header


def top_menu(msg=''):
  """ This is the "landing page" for the app.
  """
  header_str = header(title='CUNY Transfer Explorer')
  return f"""
{header_str}
<div id="introduction">
  <details>
    <summary>Introduction</summary>
    <hr>
    <p>
      In order to obtain a degree, students must complete a certain number of course credits and
      must satisfy the requirements specified for an academic program at the college that awards the
      degree. For example, to earn a bachelor’s degree at a CUNY college, students must complete 120
      credits of coursework, must satisfy a set of University-wide General Education course
      requirements known as “Pathways,” and must complete a set of course requirements for a
      college-specific “major,” such as psychology, mathematics, or English.
    </p>
    <p>
      When students transfer from one college to another, the coursework they have already completed
      should apply seamlessly to the degree requirements at their destination college. Making the
      transfer process work smoothly across a university with 20 colleges and a quarter million
      students is a major challenge; one that CUNY addresses in many ways. At a high level, these
      may be grouped as <em>university policies</em>, <em>course mappings</em>, and <em>articulation
      agreements</em>.
    </p>
    <dl id="mechanisms-list">

      <dt>University Policies</dt>
      <dd>
        Examples of University policies include uniform credit requirements for degrees (120 for
        bachelor’s; 30 for associate’s); guaranteed transferability of all credits earned at any
        CUNY college; guaranteed transfer across campuses of all Pathways requirements satisfied
        at any campuses; and transferability of SUNY General Education requirements to CUNY.
      </dd>

      <dt>Course Mappings</dt>
      <dd>
        “CUNYfirst” is the name of the Student Information System (SIS) used by all CUNY colleges.
        CUNYfirst has over a
        million<sup>&dagger;</sup> <em>transfer rules</em> that tell how courses at any CUNY college
        map onto courses at any other college.
      </dd>

      <dt>Articulation Agreements</dt>
      <dd>
        An articulation agreement is a document that tells how coursework at one college will map
        onto the degree and program requirements at another college. Articulation agreements can be
        as simple as a list of transfer rules, but they typically provide more guidance for students
        so they can make the best choices among the possible courses they take to satisfy the
        requirements at their starting college.
      </dd>

    </dl>
    <p>
    `This website is used to explore the transfer rules in CUNYfirst in manageable chunks. Faculty
     and administrators can use it to see what rules are missing or need to be changed. Students can
     use it to explore what will happen to their course credits when they transfer and/or need to
     take courses at another campus to satisfy a requirement at their home campus.
    </p>
  </details>
</div>
<div id="menu">
  <h1>Menu</h1>
  <dl id="menu-list">

    <dt><a href="/map_courses">Course Transfer Maps</a></dt>
    <dd>
      Find out how courses transfer across CUNY colleges. Results are presented in tabular form with
      cells highlighted to identify possible problems with the transfer rules.
    </dd>

    <dt><a href="/registered_programs">Academic Programs</a></dt>
    <dd>
      <p>
        Tabular information about all academic programs registered with the NYS Department of
        Education for any CUNY college. Includes information about program “variants,” such as
        programs that are shared across colleges and/or programs that can award multiple degrees
        or certificates.
      </p>
      <p>
        This information is obtained directly from a <a
        href="http://www.nysed.gov/heds/irpsl1.html">NYS Department of Education website</a>,
        which is a very nice site, but both awkward to interact with and verbose in its
        output.
      </p>
      <p>
        The tables include links to each program’s requirements, as defined in DegreeWorks.
        Parsing the requirements from the internal form used by DegreeWorks into a readable form
        is a work in progress.
      </p>
    </dd>

    <dt><a href="/review_rules">Review Transfer Rules</a></dt>
    <dd>
      Review details about, and optionally make suggestions for changing, existing transfer rules.
    </dd>

    <dt><a href="/pending">Pending Reviews</a></dt>
    <dd>
      This is a maintenance utility that shows transfer rule suggestions that have been submitted
      but not yet confirmed by the submitter. These reviews are purged if not confirmed within two
      days of submission.
    </dd>

    <dt><a href="/courses">College Course Catalogs</a></dt>
    <dd>
      Display a complete list of all the active courses for any CUNY College in standard
      college-bulletin format. But you have to say “Please,” and then be prepared for a “firehose”
      stream of information about thousands of courses. The flood of output has been known to drown
      some mobile browsers!
      <p>
        When looking at transfer rules, you can look at the catalog descriptions for just the
        courses involved in a rule.
      </p>
    </dd>
  </dl>
</div>
  <h2>Problems?</h2>
  <p>
    Please report any issues with this site to <a
    href="mailto:cvickery@qc.cuny.edu?subject='Transfer App issue'">Christopher Vickery</a>.
  </p>
  <!-- Messages -->
  <hr>
  {msg}
  """
