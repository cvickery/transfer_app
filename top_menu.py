#! /usr/local/bin/python3
"""Top-level manu for T-Rex Labs."""
from app_header import header


def top_menu(msg=''):
  """Generate the "landing page" for the app."""
  header_str = header(title='T-Rex Laboratories')

  return f"""
{header_str}
<div class="instructions">
<h1>Welcome to T-Rex Labs!</h1>
<p>
  This is a development and prototyping site for the CUNY Transfer Explorer (T-Rex) tool. While
  everything here works (<a href="mailto:cvickery@qc.cuny.edu?subject='Transfer App issue'">let me
  know</a> if not), not everything here is actually implemented in T-Rex, and T-Rex has many
  transfer-related features that were not developed here.
</p>
<p>
  Feel free to browse what’s available here. Most of the code behind this site is publicly available
  on <a href="https://github.com/cvickery">GitHub</a> if you are interested. You can reach me <a
  href="mailto:cvickery@qc.cuny.edu?subject='Transfer App Question'">by email</a> if you have
  questions about the site or the code.
</p>
<h1 style="text-align:center; color:#909">
  For the real T-Rex experience, which includes many features not developed here:<br/>
  <span id="goto-cuny">
    Use the <a href="https://explorer.cuny.edu">CUNY Transfer Explorer</a> Site.
  </span>
</h1>
</div>

<div id="menu">
  <h1>Menu</h1><hr>
  <dl id="menu-list">

    <dt><a href="/course_requirements">What Requirements Can Courses Satisfy?</a></dt
    <dd>
      <p>
        Courses can be applied to three different types of requirements: credits needed for for a
        degree or certificate, general education requirements, requirements for majors. Courses can
        also be applied to requirements for a minor, but we don’t deal with those here because
        minors are optional at CUNY.
      </p>
      <p>
        Generally, course can be applied to only one general education requirement and to only one
        requirement for a major. If a student has more than one major, it’s possible that a
        particular course can be applied to more than one major. These are called “sharing
        restrictions,” and are not currently shown here.
      </p>
      <p>
        There are two other types of restrictions that determine whether a course can actually be
        used to satisfy a particular requirement: residency and minimum grade restrictions. These
        restrictions can be particularly vexing because they can apply in so many different
        contexts, possibly with different values:
      </p>
      <ul>
        <li>Degree</li>
        <li>Program (GenEd, Major, Minor)</li>
        <li>Subrogram (aka “specialization,” “track,” “concentration,” etc. )</li>
        <li>A subset of the requirements for a program or subprogram</li>
        <li>A single requirement for a program or subprogram</li>
        <li>Just some, not all, of the courses that can satisfy a single requirement</li>
      </ul>
      <p>
        There is one other type of requirement that is different from the previous ones. CUNY has
        established certain major equivalencies across campuses. A course that has a major
        equivalency attribute is guaranteed to satisfy a particular major requirement at any other
        CUNY college. This page shows a course’s major equivalency attribute if it has one.
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

    <dt><a href="/rule_changes">Rule Changes</a></dt>
    <dd>
      <p>
        See what transfer rules have changed between two dates.
      </p>
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


    <dt><a href="/review_rules">Review Transfer Rules</a></dt>
    <dd>
      <p>This is the original prototype for the “Transfer Equivalency Review” feature available
      to authorized users on the T-Rex site. You can do anything you want here, but nothing will
      actually happen!</p>
    </dd>

    <dt><a href="/search_programs">Search Programs</a></dt>
    <dd>
      Development tool for looking up academic programs based on CIP Codes and CIP-SOC mappings.
    </dd>

    <dt><a href="/describe_programs">Describe Programs</a></dt>
    <dd>
      Development tool for cross-checking T-Rex: Describes Majors and Minors, based on Degree Works
      information about them. Does not include course requirements. (For that, see <a
      href="/requirements">Degree and Program Requirements</a>)
    </dd>

    <br/>
    <h2 class="error">The following items are in various states of disrepair!</h2>
    <hr/><br/>

    <dt><a href="/what_requirements">What Requirements Can a Course Satisfy?</a></dt>
    <dd>
      <p>
        <em>Enter a course_id or a tuple &ltinstitution discipline catalog_number&gt; and see
        information about what requirements the course satisfies at the college that offers it.
        Information includes the IDs of the Scribe blocks as well as the names of the requirements,
        and certain conditions that might affect the course’s applicability.</em>
      </p>
      <p>
        This is a development tool, used to use to verify that T-Rex and this site both “understand”
        program requirements the same way.
      </p>
    </dd>

    <dt><a href="/map_courses">Course Transfer Maps</a></dt>
    <dd>
     <p>
      Find out how courses transfer across CUNY colleges. Results are presented in tabular form with
      cells highlighted to identify possible problems with the transfer rules.
     </p>
    </dd>

    <dt><a href="/pending">Pending Reviews</a></dt>
    <dd>
      This is a maintenance utility that was used in the Review Transfer Rules prototype to show
      transfer rule suggestions that had been submitted but for which the user has not yet
      responded to an “activation” email message.
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
