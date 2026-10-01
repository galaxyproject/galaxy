import re
from pathlib import Path

from galaxy.managers.markdown_parse import (
    GALAXY_MARKDOWN_CELL_TYPES,
    validate_galaxy_markdown,
)

SECTION_WRAPPER_RELATIVE_PATH = Path("client/src/components/Markdown/Sections/SectionWrapper.vue")


def assert_markdown_valid(markdown):
    validate_galaxy_markdown(markdown)


def assert_markdown_invalid(markdown, at_line: int | None = None):
    failed = False
    try:
        validate_galaxy_markdown(markdown)
    except ValueError as e:
        failed = True
        if at_line is not None:
            assert f"Invalid line {at_line + 1}" in str(e)
    assert failed, f"Expected markdown [{markdown}] to fail validation but it did not."


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
    # assert multiple valid container is fine.
    assert_markdown_valid("""
```galaxy
job_metrics(job_id=THISFAKEID)
```

Markdown between directives.

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
    assert_markdown_invalid(
        """
```galaxy
job_metrics(job_id=THISFAKEID)
""",
        at_line=1,
    )
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
job_metrics(step="Moo Cow")
```
""")
    assert_markdown_valid("""
```galaxy
job_metrics(step='Moo Cow')
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

    assert_markdown_valid("""
```galaxy
workflow_display()
```
""")

    # Test image with a composite path (param needs to be closed, can't be misnamed i.e. pathx)
    assert_markdown_valid("""

```galaxy
history_dataset_as_image(output="cow", path="foo/bar.png")
```
""")
    assert_markdown_valid("""

```galaxy
history_dataset_as_image(output=cow, path="foo/bar.png")
```
""")
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
    assert_markdown_valid("""
```galaxy
history_dataset_link(output=moo, path="cow.png", label="my label")
```
""")
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
    assert_markdown_valid("""
```galaxy
history_dataset_link(output= moo, path= "cow.png", label= "my label")
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_link(output = moo, path = "cow.png", label = "my label")
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_link(output = moo, path ="cow.png", label= "my label" )
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_link(  output = moo, path ="cow.png", label= "my label" )
```
""")
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

    assert_markdown_valid("""
```galaxy
visualization(id=1)
```
""")
    assert_markdown_valid("""
```galaxy
visualization(foo|bar=hello)
```
""")


def test_markdown_validation_embed():
    assert_markdown_valid("""
| moo | cow |
| 1 | 2 |
""")
    assert_markdown_valid("""
| moo | cow |
| 1 | ${galaxy generate_galaxy_version()} |
""")
    assert_markdown_valid("""
| moo | cow |
| 1 | ${galaxy history_dataset_name(input=foobar)} |
""")
    assert_markdown_invalid(
        """
| moo | cow |
| 1 | ${galaxy history_dataset_name(foo=bar)} |
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
| moo | cow |
| 1 | ${galaxy generate_galaxy_version(moo=cow)} |
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
| moo | cow |
| 1 | ${galaxy invalid()} |
""",
        at_line=2,
    )


def test_markdown_validation_hid_argument():
    """Test that hid argument is valid for dataset/collection directives."""
    # Dataset directives should accept hid
    assert_markdown_valid("""
```galaxy
history_dataset_display(hid=42)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_as_image(hid=1)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_as_table(hid=5)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_embedded(hid=10)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_index(hid=3)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_info(hid=7)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_link(hid=2)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_name(hid=8)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_peek(hid=4)
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_type(hid=6)
```
""")
    # Collection directive should accept hid
    assert_markdown_valid("""
```galaxy
history_dataset_collection_display(hid=5)
```
""")
    # hid with other arguments
    assert_markdown_valid("""
```galaxy
history_dataset_as_image(hid=1, path="image.png")
```
""")
    assert_markdown_valid("""
```galaxy
history_dataset_link(hid=2, label="my link")
```
""")


def test_markdown_validation_hid_invalid_for_non_dataset_directives():
    """Test that hid argument is rejected for non-dataset directives."""
    # hid should not be valid for job directives
    assert_markdown_invalid(
        """
```galaxy
job_metrics(hid=1)
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
job_parameters(hid=1)
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
tool_stdout(hid=1)
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
tool_stderr(hid=1)
```
""",
        at_line=2,
    )
    # hid should not be valid for workflow directives
    assert_markdown_invalid(
        """
```galaxy
workflow_display(hid=1)
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
workflow_image(hid=1)
```
""",
        at_line=2,
    )
    # hid should not be valid for invocation directives
    assert_markdown_invalid(
        """
```galaxy
invocation_inputs(hid=1)
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
invocation_outputs(hid=1)
```
""",
        at_line=2,
    )
    # hid should not be valid for instance directives
    assert_markdown_invalid(
        """
```galaxy
generate_galaxy_version(hid=1)
```
""",
        at_line=2,
    )
    assert_markdown_invalid(
        """
```galaxy
history_link(hid=1)
```
""",
        at_line=2,
    )


def test_markdown_validation_fence_types():
    for cell_type in ["galaxy", "markdown", "vega", "visualization", "vitessce"]:
        body = "job_metrics(job_id=THISFAKEID)" if cell_type == "galaxy" else "{}"
        assert_markdown_valid(f"\n```{cell_type}\n{body}\n```\n")
    assert_markdown_valid("\n```vega   \n{}\n```  \n")
    # tilde fences render as plain code blocks
    assert_markdown_valid("""
~~~python
print("hello")
~~~
""")
    assert_markdown_invalid(
        """
```loom-job
job_id: 12345
```
""",
        at_line=1,
    )
    assert_markdown_invalid(
        """
Some text.

```python
print("hello")
```
""",
        at_line=3,
    )
    assert_markdown_invalid(
        """
- a list item

  ```yaml
  a: b
  ```
""",
        at_line=3,
    )
    # the client keeps the space, so the type is " galaxy"
    assert_markdown_invalid(
        """
``` galaxy
job_metrics(job_id=THISFAKEID)
```
""",
        at_line=1,
    )
    assert_markdown_invalid(
        """
````
nested
````
""",
        at_line=1,
    )
    assert_markdown_invalid("\n```Vega\n{}\n```\n", at_line=1)


def test_markdown_validation_fence_types_inside_blocks():
    assert_markdown_invalid("```\ncode\n```python\n", at_line=2)
    assert_markdown_invalid("```galaxy\n```python\n```\n", at_line=1)
    assert_markdown_invalid("~~~\n```python\n~~~\n", at_line=1)
    assert_markdown_invalid("text\n\n    ```python\n    x = 1\n", at_line=2)


def test_markdown_validation_fence_types_match_client_line_handling():
    assert_markdown_valid("text\r\n```vega\r\n{}\r\n```\r\n")
    assert_markdown_invalid("text\r\n```python\r\nx\r\n```\r\n", at_line=1)
    assert_markdown_invalid("\ufeff```python\nx\n```\n", at_line=0)
    assert_markdown_valid("text\u2028```python\n")


def test_markdown_cell_types_match_client_renderer():
    root = next(
        parent for parent in Path(__file__).resolve().parents if (parent / SECTION_WRAPPER_RELATIVE_PATH).is_file()
    )
    section_wrapper = (root / SECTION_WRAPPER_RELATIVE_PATH).read_text()
    client_cell_types = re.findall(r"name === '(\w+)'", section_wrapper)
    assert sorted(client_cell_types) == sorted(GALAXY_MARKDOWN_CELL_TYPES)


def test_markdown_validation_fence_type_error_message():
    try:
        validate_galaxy_markdown("```loom-job\njob_id: 1\n```\n")
    except ValueError as e:
        message = str(e)
    else:
        raise AssertionError("Expected loom-job fence to fail validation")
    assert "Invalid line 1" in message
    assert "[loom-job]" in message
    assert "vitessce" in message
    assert "~~~" in message
