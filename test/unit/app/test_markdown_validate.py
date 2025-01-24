from typing import Optional

from galaxy.managers.markdown_parse import validate_galaxy_markdown


def assert_markdown_valid(markdown):
    validate_galaxy_markdown(markdown)


def assert_markdown_invalid(markdown, at_line: Optional[int] = None):
    failed = False
    try:
        validate_galaxy_markdown(markdown)
    except ValueError as e:
        failed = True
        if at_line is not None:
            assert f"Invalid line {at_line + 1}" in str(e)
    assert failed, f"Expected markdown [{markdown}] to fail validation but it did not."


def test_markdown_validation():
    assert_markdown_valid(
        """
hello world
"""
    )
    assert_markdown_valid(
        """
hello ``world``

Here is some more text.

```
import <stdio>
printf('hello')
```
"""
    )
    # assert valid container is fine.
    assert_markdown_valid(
        """
```galaxy
job_metrics(job_id=THISFAKEID)
```
"""
    )
    # assert multiple valid container is fine.
    assert_markdown_valid(
        """
```galaxy
job_metrics(job_id=THISFAKEID)
```

Markdown between directives.

```galaxy
job_metrics(job_id=THISFAKEID)
```

"""
    )

    # assert valid container is fine at end of document.
    assert_markdown_valid(
        """
```galaxy
job_metrics(job_id=THISFAKEID)
```"""
    )
    # assert valid containers require container close
    assert_markdown_invalid(
        """
```galaxy
job_metrics(job_id=THISFAKEID)
""",
        at_line=1,
    )
    # assert valid containers require container close, even at end...
    assert_markdown_invalid(
        """
```galaxy
job_metrics(job_id=THISFAKEID)"""
    )
    # assert only one command allowed
    assert_markdown_invalid(
        """
```galaxy
job_metrics(job_id=THISFAKEID)
job_metrics(job_id=THISFAKEID2)
```
"""
    )
    # assert command paren is closed
    assert_markdown_invalid(
        """
```galaxy
job_metrics(job_id=THISFAKEID
```
"""
    )
    # assert command arg is named.
    assert_markdown_invalid(
        """
```galaxy
job_metrics(THISFAKEID)
```
"""
    )
    # assert quotes are fine
    assert_markdown_valid(
        """
```galaxy
job_metrics(step="Moo Cow")
```
"""
    )
    assert_markdown_valid(
        """
```galaxy
job_metrics(step='Moo Cow')
```
"""
    )
    # assert spaces require quotes
    assert_markdown_invalid(
        """
```galaxy
job_metrics(output=Moo Cow)
```
"""
    )
    # assert unmatched quotes invalid
    assert_markdown_invalid(
        """
```galaxy
job_metrics(output="Moo Cow)
```
"""
    )
    assert_markdown_invalid(
        """
```galaxy
job_metrics(output=Moo Cow")
```
"""
    )
    assert_markdown_invalid(
        """
```galaxy
job_metrics(output='Moo Cow)
```
"""
    )
    assert_markdown_invalid(
        """
```galaxy
job_metrics(output=Moo Cow')
```
"""
    )

    assert_markdown_valid(
        """
```galaxy
workflow_display()
```
"""
    )

    # Test image with a composite path (param needs to be closed, can't be misnamed i.e. pathx)
    assert_markdown_valid(
        """

```galaxy
history_dataset_as_image(output="cow", path="foo/bar.png")
```
"""
    )
    assert_markdown_valid(
        """

```galaxy
history_dataset_as_image(output=cow, path="foo/bar.png")
```
"""
    )
    assert_markdown_invalid(
        """

```galaxy
history_dataset_as_image(output="cow", path="foo/bar.png)
```
""",
        at_line=3,
    )
    assert_markdown_invalid(
        """

```galaxy
history_dataset_as_image(output="cow", pathx="foo/bar.png")
```
""",
        at_line=3,
    )

    # Test validation of three arguments
    assert_markdown_valid(
        """
```galaxy
history_dataset_link(output=moo, path="cow.png", label="my label")
```
"""
    )
    assert_markdown_invalid(
        """
```galaxy
history_dataset_link(outputx=moo, path="cow.png", label="my label")
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
history_dataset_link(output=moo, pathx="cow.png", label="my label")
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
history_dataset_link(output=moo, path="cow.png", labelx="my label")
```
""",
        at_line=2,
    )

    # Test validation of arguments with different whitespaces
    assert_markdown_valid(
        """
```galaxy
history_dataset_link(output= moo, path= "cow.png", label= "my label")
```
"""
    )
    assert_markdown_valid(
        """
```galaxy
history_dataset_link(output = moo, path = "cow.png", label = "my label")
```
"""
    )
    assert_markdown_valid(
        """
```galaxy
history_dataset_link(output = moo, path ="cow.png", label= "my label" )
```
"""
    )
    assert_markdown_valid(
        """
```galaxy
history_dataset_link(  output = moo, path ="cow.png", label= "my label" )
```
"""
    )
    assert_markdown_invalid(
        """
```galaxy
history_dataset_link(  outputx = moo, path ="cow.png", label= "my label" )
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
history_dataset_link(  output = moo, pathx ="cow.png", label= "my label" )
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
history_dataset_link(  output = moo, path ="cow.png", labelx= "my label" )
```
""",
        at_line=2,
    )

    assert_markdown_valid(
        """
```galaxy
visualization(id=1)
```
"""
    )
    assert_markdown_valid(
        """
```galaxy
visualization(foo|bar=hello)
```
"""
    )
