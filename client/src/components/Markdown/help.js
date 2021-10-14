export const markdownGeneralHelpHtml = `
<p>
    For an overview of standard Markdown please visit the <a href="https://commonmark.org/help/tutorial/" target="_blank">tutorial</a>.
</p>

<p>
    The Galaxy extensions to Markdown are represented as code blocks (using three backticks <code>\`\`\`</code>).
    They start with the line <code>\`\`\`galaxy</code> and end with the line <code>\`\`\`</code> and have a
    command with arguments that reference Galaxy objects in the middle.
</p>`;

export const datasetCommandsHtml = `
<dt><tt>history_dataset_display</tt></dt>
<dd>Embed a dataset description in the resulting document.</dd>
<dt><tt>history_dataset_collection_display</tt></dt>
<dd>Embed a dataset collection description in the resulting document.</dd>
<dt><tt>history_dataset_as_image</tt></dt>
<dd>Embed a dataset as an image in the resulting document - the dataset should be an image datatype.</dd>
<dt><tt>history_dataset_peek</tt></dt>
<dd>Embed Galaxy's metadata attribute 'peek' into the resulting document - this is datatype dependent metadata but usually this is a few lines from the start of a file.</dd>
<dt><tt>history_dataset_info</tt></dt>
<dd>Embed Galaxy's metadata attribute 'info' into the resulting document - this is datatype dependent metadata but usually this is the program output that generated the dataset.</dd>
</dl>
</div>
`;
