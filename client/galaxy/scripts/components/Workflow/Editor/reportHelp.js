const reportHelp = `
<div>
<h3>Overview</h3>

<p>
    This document Markdown document will be used to generate a report
    for invocations of this workflow. This document should be Markdown
    with embedded command for extracting and displaying parts of the workflow,
    its invocation metadata, its inputs and outputs, etc.. For an overview
    of standard Markdown visit the <a href="https://commonmark.org/help/tutorial/">commonmark.org
    tutorial</a>.
</p>

<p>
    The Galaxy extensions to Markdown are represented as code blocks, these blocks start
    with the line <tt>\`\`\`galaxy</tt> and end with the line <tt>\`\`\`</tt> and have a
    command with arguments that reference parts of the workflow in the middle.
</p>

<h3>Workflow Commands</h3>

<p>
    These commands to do not take any arguments and reference the whole workflow. For
    instance, the following example would display a representation of the workflow in the
    resulting report:
</p>

<pre>
\`\`\`galaxy
workflow_display()
\`\`\`
</pre>
<dl>
<dt><tt>workflow_display</tt></dt>
<dd>Embed a description of the workflow itself in the resulting report.</dd>
<dt><tt>invocation_inputs</tt></dt>
<dd>Embed the labeled workflow inputs in the resulting report.</dd>
<dt><tt>invocation_outputs</tt></dt>
<dd>Embed the labeled workflow outputs in the resulting report.</dd>
</dl>

<h3>Step Commands</h3>

<p>
    These commands reference a workflow step label and refer to job corresponding
    to that step. A current limitation is the report will break if these refer to
    a collection mapping step, these must identify a single job. For instance, the
    following example would show the job parameters the step labeled 'qc' was run
    with:
</p>

<pre>
\`\`\`galaxy
job_parameters(step=qc)
\`\`\`
</pre>


<dt><tt>tool_stderr</tt></dt>
<dd>Embed the tool standard error stream for this step in the resulting report.</dd>
<dt><tt>tool_stdout</tt></dt>
<dd>Embed the tool standard output stream for this step in the resulting report.</dd>
<dt><tt>job_metrics</tt></dt>
<dd>Embed the job metrics for this step in the resulting report (if user has permission).</dd>
<dt><tt>job_parameters</tt></dt>
<dd>Embed the tool parameters for this step in the resulting report.</dd>

<h3>Input/Output Commands</h3>

<p>
    These commands reference a workflow input or output by label. For instance, the
    following example would display the dataset collection corresponding to output "Merged BAM":
</p>

<pre>
\`\`\`galaxy
history_dataset_collection_display(output="Merged Bam")
\`\`\`
</pre>

<dt><tt>history_dataset_display</tt></dt>
<dd>Embed a dataset description in the resulting report.</dd>
<dt><tt>history_dataset_collection_display</tt></dt>
<dd>Embed a dataset collection description in the resulting report.</dd>
<dt><tt>history_dataset_as_image</tt></dt>
<dd>Embed a dataset as an image in the resulting report - the dataset should be an image datatype.</dd>
<dt><tt>history_dataset_peek</tt></dt>
<dd>Embed Galaxy's metadata attribute 'peek' into the resulting report - this is datatype dependent metadata but usually this is a few lines from the start of a file.</dd>
<dt><tt>history_dataset_info</tt></dt>
<dd>Embed Galaxy's metadata attribute 'info' into the resulting report - this is datatype dependent metadata but usually this is the program output that generated the dataset.</dd>
</dl>
</div>
`;

import $ from "jquery";
import { hide_modal, show_modal } from "layout/modal";

export function showReportHelp() {
    const reportHelpBody = $(reportHelp);
    show_modal("Workflow Invocation Report Help", reportHelpBody, {
        Ok: hide_modal
    });
}
