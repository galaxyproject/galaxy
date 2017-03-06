"""Manage the files in this directory."""
import urllib2

DRAFTS = ["3"]
SCHEMAS_URL = "https://raw.githubusercontent.com/common-workflow-language/common-workflow-language/master/"

CWL_FILES = [
    "args.py",
    "bwa-mem-tool.cwl",
    "cat-job.json",
    "cat1-tool.cwl",
    "cat3-tool.cwl",
    "cat2-tool.cwl",
    "cat4-tool.cwl",
    "cat-n-job.json",
    "count-lines1-wf.cwl",
    "count-lines2-wf.cwl",
    "empty.json",
    "env-tool1.cwl",
    "env-tool2.cwl",
    "env-job.json",
    "hello.txt",
    "index.py",
    "optional-output.cwl",
    "number.txt",
    "null-expression1-job.json",
    "null-expression2-job.json",
    "null-expression1-tool.cwl",
    "null-expression2-tool.cwl",
    "params.cwl",
    "params2.cwl",
    "params_inc.yml",
    "parseInt-job.json",
    "parseInt-tool.cwl",
    "rename.cwl",
    "rename-job.json",
    "sorttool.cwl",
    "wc-tool.cwl",
    "wc2-tool.cwl",
    "wc3-tool.cwl",
    "wc4-tool.cwl",
    "wc-job.json",
    "whale.txt",
]

for draft in DRAFTS:
    for cwl_file in CWL_FILES:
        url = SCHEMAS_URL + ("draft-%s/draft-%s/%s" % (draft, draft, cwl_file))
        response = urllib2.urlopen(url)
        open("draft%s/%s" % (draft, cwl_file), "w").write(response.read())
