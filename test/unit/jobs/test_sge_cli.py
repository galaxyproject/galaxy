from galaxy.jobs.runners.util.cli.job.sge import Sge
from galaxy.model import Job


STATUS_XML_STRING = """<job_info  xmlns:xsd="http://arc.liv.ac.uk/repos/darcs/sge/source/dist/util/resources/schemas/qstat/qstat.xsd">
  <queue_info>
    <job_list state="running">
      <JB_job_number>7440828</JB_job_number>
      <JAT_prio>0.14478</JAT_prio>
      <JB_name>NVT-octyl-7ns</JB_name>
      <JB_owner>amith</JB_owner>
      <state>r</state>
      <JAT_start_time>2019-04-09T16:17:20</JAT_start_time>
      <queue_name>UI@argon-lc-i18-21.hpc</queue_name>
      <slots>56</slots>
    </job_list>
    <job_list state="running">
      <JB_job_number>6148294</JB_job_number>
      <JAT_prio>0.59493</JAT_prio>
      <JB_name>Ebola_time0</JB_name>
      <JB_owner>jiangcxu</JB_owner>
      <state>r</state>
      <JAT_start_time>2019-02-28T23:27:30</JAT_start_time>
      <queue_name>UI@argon-lc-i18-20.hpc</queue_name>
      <slots>56</slots>
    </job_list>
  </queue_info>
</job_info>"""
JOB_IDS = ['7440828', '6148294']


def test_parse_status():
    sge = Sge()
    rval = sge.parse_status(status=STATUS_XML_STRING, job_ids=JOB_IDS)
    assert len(rval) == 2
    assert rval['7440828'] == Job.states.RUNNING
    assert rval['6148294'] == Job.states.RUNNING
