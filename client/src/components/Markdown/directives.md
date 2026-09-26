# Galaxy Markdown Directive Reference

Generated from `directives.yml` by `scripts/markdown_directives_doc.py` (`make client-gen-markdown-directives`). Do not edit by hand.

## Syntax

**Block** — works for every directive; required in workflow report templates:

````
```galaxy
directive_name(arg=value)
```
````

One directive per fenced `galaxy` block. **Inline** (`${galaxy ...}`) works only for the [embeddable directives](#embeddable-directives).

## Argument value types

| Type      | Meaning                                                             |
| --------- | ------------------------------------------------------------------- |
| `label`   | Workflow input/output/step label; resolved to an ID per invocation. |
| `id`      | Encoded (export) or numeric (internal) object ID.                   |
| `int`     | Integer.                                                            |
| `boolean` | `true` or `false`.                                                  |
| `enum`    | One of a fixed set of values.                                       |
| `string`  | Free display text.                                                  |
| `path`    | File within a composite / extra-files dataset.                      |

## Addressing contexts

The same directive accepts different parameters depending on how the object is referenced:

| Context      | Use                                                       |
| ------------ | --------------------------------------------------------- |
| `report`     | Workflow report template — labels resolve per invocation. |
| `page`       | Page / direct contexts — encoded or numeric IDs.          |
| `notebook`   | History-relative reference (notebooks).                   |
| `invocation` | Invocation reference — usually injected automatically.    |

## Universal argument

`collapse="<link text>"` — wraps a block directive in a collapsible section. Valid on every directive.

---

## Dataset directives

| Directive                  | Embed | Requires             | Renders                                                     |
| -------------------------- | ----- | -------------------- | ----------------------------------------------------------- |
| `history_dataset_display`  |       | `history_dataset_id` | Interactive dataset card with view/import/download options. |
| `history_dataset_as_image` | ✅    | `history_dataset_id` | Dataset embedded as an image.                               |
| `history_dataset_index`    |       | `history_dataset_id` | File/folder listing of a composite dataset.                 |
| `history_dataset_embedded` |       | `history_dataset_id` | Raw dataset content inline.                                 |
| `history_dataset_as_table` |       | `history_dataset_id` | Tabular dataset as a formatted table.                       |
| `history_dataset_type`     | ✅    | `history_dataset_id` | Datatype string as text.                                    |
| `history_dataset_link`     |       | `history_dataset_id` | Download link for a dataset.                                |
| `history_dataset_name`     | ✅    | `history_dataset_id` | Dataset name as text.                                       |
| `history_dataset_peek`     |       | `history_dataset_id` | Dataset "peek" preview.                                     |
| `history_dataset_info`     |       | `history_dataset_id` | Dataset "info" metadata.                                    |

### `history_dataset_display`

Display a dataset and relevant options for viewing, importing, downloading,
and visualization in the resulting document. To embed a dataset directly
into the document use the "history_dataset_embedded" / "Embedded Dataset"
directive.

| Parameter            | Type    | Context      | Default | Description                                                        |
| -------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`    | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |

### `history_dataset_as_image`

Embed a dataset in the resulting document as an image. This only works for simple image
types. This can be used to present graphs and other visual summaries of an analysis into
a Galaxy Markdown document summary.

| Parameter            | Type    | Context      | Default | Description                                                        |
| -------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`    | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |
| `path`               | `path`  |              |         | File within a composite / extra-files dataset.                     |

### `history_dataset_index`

For Galaxy composite datasets (datasets that consist on multiple files), this option will
display the contents of the composite dataset as files and folders in the resulting document.

| Parameter            | Type    | Context      | Default | Description                                                        |
| -------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`    | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |
| `path`               | `path`  |              |         | File within a composite / extra-files dataset.                     |

### `history_dataset_embedded`

| Parameter            | Type    | Context      | Default | Description                                                        |
| -------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`    | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |

### `history_dataset_as_table`

Embed a dataset in the resulting document as a table. This only works for datasets with tabular
datatypes. This command works a lot like "history_dataset_embedded" but provides specialized options
for controlling the way tabular data is displayed in the resulting document.

| Parameter             | Type      | Context      | Default | Description                                                        |
| --------------------- | --------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`              | `label`   | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`               | `label`   | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                 | `int`     | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id`  | `id`      | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`       | `id`      | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |
| `title`               | `string`  |              |         | Table title.                                                       |
| `footer`              | `string`  |              |         | Table footer.                                                      |
| `compact`             | `boolean` |              | `false` | Compact row height.                                                |
| `show_column_headers` | `boolean` |              | `true`  | Show column headers.                                               |
| `path`                | `path`    |              |         | File within a composite / extra-files dataset.                     |

### `history_dataset_type`

| Parameter            | Type    | Context      | Default | Description                                                        |
| -------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`    | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |

### `history_dataset_link`

| Parameter            | Type     | Context      | Default | Description                                                        |
| -------------------- | -------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label`  | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label`  | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`    | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`     | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`     | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |
| `label`              | `string` |              |         | Link text.                                                         |
| `path`               | `path`   |              |         | File within a composite / extra-files dataset.                     |

### `history_dataset_name`

| Parameter            | Type    | Context      | Default | Description                                                        |
| -------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`    | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |

### `history_dataset_peek`

Display a dataset metadata's "peek" field in the resulting document - this is datatype dependent
metadata but usually this is a few lines from the start of a file.

| Parameter            | Type    | Context      | Default | Description                                                        |
| -------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`    | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |

### `history_dataset_info`

Display a dataset metadata's "info" field in the resulting document. This info field is
usually based on the output of the tool run and sometimes contains useful metadata about a
dataset.

| Parameter            | Type    | Context      | Default | Description                                                        |
| -------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`             | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`              | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_id` | `id`    | `page`       |         | Encoded (export) or numeric (internal) dataset ID.                 |
| `invocation_id`      | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |

---

## Collection directives

| Directive                            | Embed | Requires                        | Renders                                         |
| ------------------------------------ | ----- | ------------------------------- | ----------------------------------------------- |
| `history_dataset_collection_display` |       | `history_dataset_collection_id` | Collection browser for paired/list collections. |

### `history_dataset_collection_display`

Display a dataset collection and relevant options for viewing, importing, downloading
in the resulting document.

| Parameter                       | Type    | Context      | Default | Description                                                        |
| ------------------------------- | ------- | ------------ | ------- | ------------------------------------------------------------------ |
| `output`                        | `label` | `report`     |         | Workflow output label, resolved per invocation (report templates). |
| `input`                         | `label` | `report`     |         | Workflow input label, resolved per invocation (report templates).  |
| `hid`                           | `int`   | `notebook`   |         | History item hid.                                                  |
| `history_dataset_collection_id` | `id`    | `page`       |         | Encoded or numeric dataset collection ID.                          |
| `invocation_id`                 | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution.   |

---

## Invocation directives

| Directive            | Embed | Requires        | Renders                                |
| -------------------- | ----- | --------------- | -------------------------------------- |
| `history_link`       |       | `history_id`    | Link to import the referenced history. |
| `invocation_inputs`  |       | `invocation_id` | Summary of all workflow inputs.        |
| `invocation_outputs` |       | `invocation_id` | Summary of all workflow outputs.       |
| `invocation_time`    | ✅    | `invocation_id` | Invocation run timestamp.              |

### `history_link`

Add a link to import the history the workflow invocation was executed in.

| Parameter       | Type | Context      | Default | Description                                                      |
| --------------- | ---- | ------------ | ------- | ---------------------------------------------------------------- |
| `history_id`    | `id` | `page`       |         | Encoded or numeric history ID.                                   |
| `invocation_id` | `id` | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

### `invocation_inputs`

| Parameter       | Type | Context      | Default | Description                                                      |
| --------------- | ---- | ------------ | ------- | ---------------------------------------------------------------- |
| `invocation_id` | `id` | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

### `invocation_outputs`

| Parameter       | Type | Context      | Default | Description                                                      |
| --------------- | ---- | ------------ | ------- | ---------------------------------------------------------------- |
| `invocation_id` | `id` | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

### `invocation_time`

Display this workflow run's invocation time in the resulting document.

| Parameter       | Type | Context      | Default | Description                                                      |
| --------------- | ---- | ------------ | ------- | ---------------------------------------------------------------- |
| `invocation_id` | `id` | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

---

## Workflow directives

| Directive          | Embed | Requires      | Renders                                      |
| ------------------ | ----- | ------------- | -------------------------------------------- |
| `workflow_display` |       | `workflow_id` | Step-by-step text description of a workflow. |
| `workflow_image`   |       | `workflow_id` | SVG workflow diagram.                        |
| `workflow_license` | ✅    | `workflow_id` | Workflow license information.                |

### `workflow_display`

Embed a text description of this workflow's steps in the resulting document.

| Parameter             | Type  | Context      | Default | Description                                                      |
| --------------------- | ----- | ------------ | ------- | ---------------------------------------------------------------- |
| `workflow_id`         | `id`  | `page`       |         | Stored workflow ID.                                              |
| `workflow_checkpoint` | `int` | `page`       |         | Workflow version index.                                          |
| `invocation_id`       | `id`  | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

### `workflow_image`

Embed a rough image this workflow in the resulting document.

| Parameter             | Type                    | Context      | Default | Description                                                      |
| --------------------- | ----------------------- | ------------ | ------- | ---------------------------------------------------------------- |
| `workflow_id`         | `id`                    | `page`       |         | Stored workflow ID.                                              |
| `workflow_checkpoint` | `int`                   | `page`       |         | Workflow version index.                                          |
| `invocation_id`       | `id`                    | `invocation` |         | Invocation ID; usually injected automatically during resolution. |
| `size`                | enum (`sm`, `md`, `lg`) |              | `lg`    | Image width (sm=300px, md=550px, lg=100%).                       |

### `workflow_license`

Display this workflow's license in the resulting document.

| Parameter       | Type | Context      | Default | Description                                                      |
| --------------- | ---- | ------------ | ------- | ---------------------------------------------------------------- |
| `workflow_id`   | `id` | `page`       |         | Stored workflow ID.                                              |
| `invocation_id` | `id` | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

---

## Job directives

| Directive        | Embed | Requires | Renders                          |
| ---------------- | ----- | -------- | -------------------------------- |
| `job_metrics`    |       | `job_id` | Runtime metrics table for a job. |
| `job_parameters` |       | `job_id` | Tool parameters table for a job. |
| `tool_stdout`    |       | `job_id` | Tool standard output for a job.  |
| `tool_stderr`    |       | `job_id` | Tool standard error for a job.   |

### `job_metrics`

Embed the job metrics for this job in the resulting document (if Galaxy is configured and you have
permission).

| Parameter                     | Type    | Context      | Default | Description                                                      |
| ----------------------------- | ------- | ------------ | ------- | ---------------------------------------------------------------- |
| `step`                        | `label` | `report`     |         | Workflow step label, resolved per invocation (report templates). |
| `job_id`                      | `id`    | `page`       |         | Encoded or numeric job ID.                                       |
| `implicit_collection_jobs_id` | `id`    | `page`       |         | Mapped-collection job group ID.                                  |
| `invocation_id`               | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

### `job_parameters`

Embed the tool parameters for a job in the resulting document.

| Parameter                     | Type     | Context      | Default | Description                                                      |
| ----------------------------- | -------- | ------------ | ------- | ---------------------------------------------------------------- |
| `step`                        | `label`  | `report`     |         | Workflow step label, resolved per invocation (report templates). |
| `job_id`                      | `id`     | `page`       |         | Encoded or numeric job ID.                                       |
| `implicit_collection_jobs_id` | `id`     | `page`       |         | Mapped-collection job group ID.                                  |
| `invocation_id`               | `id`     | `invocation` |         | Invocation ID; usually injected automatically during resolution. |
| `footer`                      | `string` |              |         | Table footer.                                                    |

### `tool_stdout`

Embed the tool standard output stream for a job in the resulting document.

| Parameter                     | Type    | Context      | Default | Description                                                      |
| ----------------------------- | ------- | ------------ | ------- | ---------------------------------------------------------------- |
| `step`                        | `label` | `report`     |         | Workflow step label, resolved per invocation (report templates). |
| `job_id`                      | `id`    | `page`       |         | Encoded or numeric job ID.                                       |
| `implicit_collection_jobs_id` | `id`    | `page`       |         | Mapped-collection job group ID.                                  |
| `invocation_id`               | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

### `tool_stderr`

Embed the tool standard error stream for a job in the resulting document.

| Parameter                     | Type    | Context      | Default | Description                                                      |
| ----------------------------- | ------- | ------------ | ------- | ---------------------------------------------------------------- |
| `step`                        | `label` | `report`     |         | Workflow step label, resolved per invocation (report templates). |
| `job_id`                      | `id`    | `page`       |         | Encoded or numeric job ID.                                       |
| `implicit_collection_jobs_id` | `id`    | `page`       |         | Mapped-collection job group ID.                                  |
| `invocation_id`               | `id`    | `invocation` |         | Invocation ID; usually injected automatically during resolution. |

---

## Visualization directive

| Directive       | Embed | Requires             | Renders                            |
| --------------- | ----- | -------------------- | ---------------------------------- |
| `visualization` |       | `history_dataset_id` | Galaxy plugin-based visualization. |

### `visualization`

Embed a Galaxy visualization in the resulting document. Accepts arguments specific to the
selected visualization plugin; these arguments are not validated by the Galaxy Markdown parser.

---

## Utility & instance directives

| Directive                    | Embed | Requires | Renders                                |
| ---------------------------- | ----- | -------- | -------------------------------------- |
| `generate_time`              | ✅    | —        | Current time at generation.            |
| `generate_galaxy_version`    | ✅    | —        | Galaxy version string at generation.   |
| `instance_access_link`       | ✅    | —        | Link to the Galaxy instance.           |
| `instance_resources_link`    | ✅    | —        | Link to instance resources.            |
| `instance_help_link`         | ✅    | —        | Link to instance help.                 |
| `instance_support_link`      | ✅    | —        | Link to instance support.              |
| `instance_citation_link`     | ✅    | —        | Link to instance citation information. |
| `instance_terms_link`        | ✅    | —        | Link to instance terms.                |
| `instance_organization_link` | ✅    | —        | Link to the instance's organization.   |

### `generate_time`

Report the current time of report generation.

Warning: This is the time the report was generated and not the time of
an analysis. This option makes the most sense for PDF generation of reports
designed for external archiving or printing.

### `generate_galaxy_version`

Report the current Galaxy version at the time report generation.

Warning: This is the Galaxy version at the time the report was generated and
not the time of an analysis. This option makes the most sense for PDF generation
of reports designed for external archiving or printing.

---

## Embeddable directives

Inline `${galaxy ...}` syntax is supported only for these directives; all others require block syntax.

- `history_dataset_as_image`
- `history_dataset_type`
- `history_dataset_name`
- `invocation_time`
- `workflow_license`
- `generate_time`
- `generate_galaxy_version`
- `instance_access_link`
- `instance_resources_link`
- `instance_help_link`
- `instance_support_link`
- `instance_citation_link`
- `instance_terms_link`
- `instance_organization_link`
