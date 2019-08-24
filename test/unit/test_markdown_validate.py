from galaxy.managers.markdown_util import validate_galaxy_markdown


def assert_markdown_valid(markdown):
    validate_galaxy_markdown(markdown)


def assert_markdown_invalid(markdown, at_line=None):
    failed = False
    try:
        validate_galaxy_markdown(markdown)
    except Exception as e:
        failed = True
        print(e)
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
```{galaxy_job_metrics job_id=THISFAKEID}
```
""")
    # assert valid container is fine.
    assert_markdown_valid("""
```{galaxy_job_metrics job_id=THISFAKEID}
```""")
    # assert valid containers require container close
    assert_markdown_invalid("""
```{galaxy_job_metrics job_id=THISFAKEID}
foo
""", at_line=1)
    # assert valid containers require container close, even at end...
    assert_markdown_invalid("""
```{galaxy_job_metrics job_id=THISFAKEID""")

    # assert valid containers require container close, even at end...
    assert_markdown_invalid("""
```{galaxy_not_a_command}
```""")
    assert_markdown_invalid("""
```{not_a_command}
```""")
