import { datasetCommandsHtml, markdownGeneralHelpHtml } from "components/Markdown/help";

const markdownHelp = `
<div>
<h3>Overview</h3>

<p>
    This document Markdown document will be used to generate your Galaxy Page.
    This document should be Markdown with embedded command for extracting and
    displaying Galaxy objects and their metadata. 
</p>

${markdownGeneralHelpHtml}

<h3>History Contents Commands</h3>

<p>
    These commands reference a dataset. For instance, the following examples would display
    the dataset collection corresponding to a Galaxy dataset collection ID and display a
    single dataset as an image corresponding to a Galaxy dataset ID.
</p>

<pre>
\`\`\`galaxy
history_dataset_collection_display(history_dataset_collection_id=33b43b4e7093c91f)
\`\`\`
</pre>

<pre>
\`\`\`galaxy
history_dataset_as_image(history_dataset_id=33b43b4e7093c91f)
\`\`\`
</pre>


${datasetCommandsHtml}

<h3>Workflow Commands</h3>

<p>
    These commands reference a workflow (currently only one). The following example would
    display a representation of the workflow in the resulting Galaxy Page:
</p>

<pre>
\`\`\`galaxy
workflow_display(workflow_id=33b43b4e7093c91f>)
\`\`\`
</pre>

<dl>
<dt><tt>workflow_display</tt></dt>
<dd>Embed a description of the workflow itself in the resulting document.</dd>
</dl>

<h3>Job Commands</h3>

<p>
    These commands reference a Galaxy job.For instance, the
    following example would show the job parameters the job ID 33b43b4e7093c91f:
</p>

<pre>
\`\`\`galaxy
job_parameters(job_id=33b43b4e7093c91f)
\`\`\`
</pre>

<dt><tt>tool_stderr</tt></dt>
<dd>Embed the tool standard error stream for this job in the resulting document.</dd>
<dt><tt>tool_stdout</tt></dt>
<dd>Embed the tool standard output stream for this job in the resulting document.</dd>
<dt><tt>job_metrics</tt></dt>
<dd>Embed the job metrics for this job in the resulting document (if Galaxy is configured and you have permission).</dd>
<dt><tt>job_parameters</tt></dt>
<dd>Embed the tool parameters for this job in the resulting document.</dd>
`;

import $ from "jquery";
import { hide_modal, show_modal } from "layout/modal";

export function showMarkdownHelp() {
    const markdownHelpBody = $(markdownHelp);
    show_modal("Pages Markdown Help", markdownHelpBody, {
        Ok: hide_modal,
    });
}
