DOCUMENT = """
# Dynamically Generated Report

Here is a peek of the exciting stuff we did:

```galaxy
history_dataset_peek(output=output_text)
```

The tool produced the following image image:

```galaxy
history_dataset_as_image(output=output_image)
```

We produced a table that looks like this:

```galaxy
history_dataset_as_table(output=output_table, header="Table Header", footer="A description of the table", compact=true)
```

The same table as embedded and using the full dataset display:

(embed)

```galaxy
history_dataset_embedded(output=output_table)
```

(display)

```galaxy
history_dataset_display(output=output_table)
```

The standard output for this tool execution is:

```galaxy
tool_stdout()
```

This is my document and I have populated the title from a parameter.
"""

with open("output_report.md", "w") as f:
    f.write(DOCUMENT)
