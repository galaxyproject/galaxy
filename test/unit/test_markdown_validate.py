from galaxy.managers.markdown_util import validate_galaxy_markdown


def assert_markdown_valid(markdown):
    validate_galaxy_markdown(markdown)


def assert_markdown_invalid(markdown, at_line=None):
    failed = False
    try:
        validate_galaxy_markdown(markdown)
    except Exception as e:
        failed = True
        if at_line is not None:
            assert "Invalid line %d" % (at_line + 1) in str(e)
    assert failed, "Expected markdown [%s] to fail validation but it did not." % markdown


def test_markdown_validation():
    assert_markdown_valid("""
hello world
""")
    assert_markdown_valid("""
hello ``world``

Here is some more text.

```
import <stdio>
printf('hello')
```
""")
    # assert valid container is fine.
    assert_markdown_valid("""
```galaxy
job_metrics(job_id=THISFAKEID)
```
""")
    # assert valid container is fine at end of document.
    assert_markdown_valid("""
```galaxy
job_metrics(job_id=THISFAKEID)
```""")
    # assert valid containers require container close
    assert_markdown_invalid("""
```galaxy
job_metrics(job_id=THISFAKEID)
""", at_line=1)
    # assert valid containers require container close, even at end...
    assert_markdown_invalid("""
```galaxy
job_metrics(job_id=THISFAKEID)""")
    # assert only one command allowed
    assert_markdown_invalid("""
```galaxy
job_metrics(job_id=THISFAKEID)
job_metrics(job_id=THISFAKEID2)
```
""")
    # assert command paren is closed
    assert_markdown_invalid("""
```galaxy
job_metrics(job_id=THISFAKEID
```
""")
    # assert command arg is named.
    assert_markdown_invalid("""
```galaxy
job_metrics(THISFAKEID)
```
""")
    # assert quotes are fine
    assert_markdown_valid("""
```galaxy
job_metrics(output="Moo Cow")
```
""")
    assert_markdown_valid("""
```galaxy
job_metrics(output='Moo Cow')
```
""")
    # assert spaces require quotes
    assert_markdown_invalid("""
```galaxy
job_metrics(output=Moo Cow)
```
""")
    # assert unmatched quotes invalid
    assert_markdown_invalid("""
```galaxy
job_metrics(output="Moo Cow)
```
""")
    assert_markdown_invalid("""
```galaxy
job_metrics(output=Moo Cow")
```
""")
    assert_markdown_invalid("""
```galaxy
job_metrics(output='Moo Cow)
```
""")
    assert_markdown_invalid("""
```galaxy
job_metrics(output=Moo Cow')
```
""")
