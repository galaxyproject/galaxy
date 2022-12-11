<template>
    <div class="p-4">
        <h2 class="h-md">Workflow Reports</h2>
        <p>
            The <b>Markdown</b> document you see will be used to generate a workflow invocation report. You can use
            Markdown with embedded commands for extracting and displaying parts of the workflow, its invocation
            metadata, its inputs and outputs, etc..
        </p>
        <div v-html="markdownGeneralHelpHtml" />
        <h2 class="h-md">Workflow Commands</h2>
        <p>
            These commands do not take any arguments and do reference the whole workflow. For instance, the following
            example would display a representation of the workflow in the resulting report:
        </p>
        <pre>
```galaxy
workflow_display()
```
</pre
        >
        <dl>
            <dt><tt>workflow_display</tt></dt>
            <dd>Embed a description of the workflow itself in the resulting report.</dd>
            <dt><tt>invocation_inputs</tt></dt>
            <dd>Embed the labeled workflow inputs in the resulting report.</dd>
            <dt><tt>invocation_outputs</tt></dt>
            <dd>Embed the labeled workflow outputs in the resulting report.</dd>
        </dl>
        <h2 class="h-md">Step Commands</h2>
        <p>
            These commands reference a workflow step label and refer to job corresponding to that step. A current
            limitation is the report will break if these refer to a collection mapping step, these must identify a
            single job. For instance, the following example would show the job parameters the step labeled 'qc' was run
            with:
        </p>
        <pre>
```galaxy
job_parameters(step="qc")
```
</pre
        >
        <p>It is also possible to reference a single job parameter</p>

        <pre>
```galaxy
job_parameters(step="qc", param="parameter_text")
```
</pre
        >
        <dt><tt>tool_stderr</tt></dt>
        <dd>Embed the tool standard error stream for this step in the resulting report.</dd>
        <dt><tt>tool_stdout</tt></dt>
        <dd>Embed the tool standard output stream for this step in the resulting report.</dd>
        <dt><tt>job_metrics</tt></dt>
        <dd>Embed the job metrics for this step in the resulting report (if user has permission).</dd>
        <dt><tt>job_parameters</tt></dt>
        <dd>Embed the tool parameters for this step in the resulting report.</dd>
        <h2 class="h-md">Input/Output Commands</h2>
        <p>
            These commands reference a workflow input or output by label. For instance, the following example would
            display the dataset collection corresponding to output "Merged BAM":
        </p>

        <pre>
```galaxy
history_dataset_collection_display(output="Merged Bam")
```
</pre
        >
        <div v-html="datasetCommandsHtml" />
    </div>
</template>

<script>
import { datasetCommandsHtml, markdownGeneralHelpHtml } from "components/Markdown/help";
export default {
    data() {
        return {
            datasetCommandsHtml,
            markdownGeneralHelpHtml,
        };
    },
};
</script>
