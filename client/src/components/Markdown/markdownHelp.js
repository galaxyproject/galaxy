import { markdownGeneralHelpHtml } from "components/Markdown/help";

const markdownHelp = `
<p>
This document is used to generate your Galaxy Page.
It is written in Markdown with some specific features
for extracting and displaying Galaxy objects and their metadata.
</p>

${markdownGeneralHelpHtml}
<h3>Inserting Menu</h3>
<p>You can embed Galaxy objects interactively by using the "Insert Objects" panel in the left
sidebar. Clicking on an object type will bring up a wizard that will guide you through
the parameter selection.</p>
<h3>Examples</h3>
<p>
Display the <strong>dataset collection</strong> corresponding to an ID of 33b43b4e7093c91f.<br>
<pre>\`\`\`galaxy
history_dataset_collection_display(history_dataset_collection_id=33b43b4e7093c91f)
\`\`\`</pre>
</p>
<p>
Display a <strong>single dataset</strong> as an image (the dataset should be an image).
<pre>\`\`\`galaxy
history_dataset_as_image(history_dataset_id=33b43b4e7093c91f)
\`\`\`</pre>
</p>
<p>
Display a representation of a <strong>workflow</strong>.
<pre>\`\`\`galaxy
workflow_display(workflow_id=33b43b4e7093c91f>)
\`\`\`</pre>
</p>
<p>
Display the <strong>job parameters</strong> for the given job.
<pre>\`\`\`galaxy
job_parameters(job_id=33b43b4e7093c91f)
\`\`\`</pre>
</p>
<p>
Insert a custom <strong>visualization</strong> based on a dataset.
<pre>\`\`\`galaxy
visualization(visualization_id=nvd3_bar_stacked, history_dataset_id=d1dfd0042d880a92, x_axis_label="X-axis", x_axis_type|type="auto", y_axis_label="Y-axis", y_axis_type|type="auto", show_legend="true", groups_0|key="Data label")
\`\`\`</pre>
</p>
`;

import $ from "jquery";
import { hide_modal, show_modal } from "layout/modal";

export function showMarkdownHelp() {
    const markdownHelpBody = $(markdownHelp);
    show_modal("Pages Markdown Help", markdownHelpBody, {
        Ok: hide_modal,
    });
}
