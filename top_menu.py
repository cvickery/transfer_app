#! /usr/local/bin/python3

from app_header import header


def top_menu(msg=''):
  """ This is the "landing page" for the app.
  """
  header_str = header(title='CUNY Transfer Application')
  return f"""
    {header_str}
    <p>
      There are over a million<sup>&dagger;</sup> rules that tell how courses transfer among CUNY
      colleges. This site lets you see what rules exist (or not), to provide feedback about existing
      rules, and to track the status of the rule review process.
    </p>
    <p>
      The material is broken down so you can select just the combinations of colleges, disciplines,
      and courses that you are interested in.
    </p>
    <dl>

      <dt><a href="/map_courses">Course Transfer Maps</a></dt>
      <dd>
        Find which colleges a course or set of courses transfers to or from. Results are presented
        in tabular form with cells highlighted to identify possible problems.
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
        stream of information about thousands of courses. The mass of output has been known to drown
        some mobile browsers.
      </dd>

    </dl>
    <h2>Problems?</h2>
    <p>
      Please report any issues with this site to <a
      href="mailto:cvickery@qc.cuny.edu?subject='Transfer App issue'">Christopher Vickery</a>.
    </p>
    <!-- Messages -->
    <hr>
    {msg}
  """
