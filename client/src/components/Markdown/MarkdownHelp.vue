<script setup lang="ts">
import { computed, ref } from "vue";

interface MarkdownHelpProps {
    mode: "report" | "page";
}

const props = defineProps<MarkdownHelpProps>();

const show = ref(false);
const page = computed(() => props.mode == "page");
const title = computed(() => {
    if (page.value) {
        return "Markdown Help for Pages";
    } else {
        return "Markdown Help for Invocation Reports";
    }
});

function showMarkdownHelp() {
    show.value = true;
}

defineExpose({
    showMarkdownHelp,
});
</script>

<template>
    <b-modal v-model="show" hide-footer>
        <template v-slot:modal-title>
            <h2 class="mb-0">{{ title }}</h2>
        </template>
        <div>
            <h3>Overview</h3>
            <p>
                <span v-if="page"> This Markdown document will be used to generate your Galaxy Page. </span>
                <span v-else> This Markdown document will be used to generate your workflow invocation report. </span>
                This document should be Markdown with embedded commands for extracting and displaying Galaxy objects
                and/or their metadata.
            </p>

            <p>
                For an overview of standard Markdown visit the
                <a href="https://commonmark.org/help/tutorial/">commonmark.org tutorial</a>.
            </p>

            <p>
                The Galaxy extensions to Markdown are represented as code blocks, these blocks start with the line
                <tt>```galaxy</tt> and end with the line <tt>```</tt> and have a command with arguments between these
                lines.
                <span v-if="page">
                    These arguments reference your Galaxy objects such as datasets, jobs, and workflows.
                </span>
                <span v-else>
                    These arguments reference parts of your workflow such as steps, inputs, and outputs by label in the
                    middle.
                </span>
            </p>

            <h3>History Contents Commands</h3>

            <p>
                These commands reference a dataset or dataset collection. For instance, the following examples would
                display the dataset collection metadata and would embed a dataset into the document as an image.

                <span v-if="page">
                    These elements are referenced by object IDs used by the Galaxy API. The Markdown editor will let you
                    pick objects graphically but they will be embedded into the Markdown with these IDs.
                </span>

                <span v-else>
                    These elements are referenced by input or output labels for the workflow. If a dataset or collection
                    you'd like to reference is not available for selection in the Markdown editor, be sure to assign a
                    label to the object in the workflow editor first.
                </span>
            </p>

            <pre v-if="page">
```galaxy
history_dataset_collection_display(history_dataset_collection_id=33b43b4e7093c91f)
```
</pre
            >
            <pre v-else>
```galaxy
history_dataset_collection_display(output=mapped_bams)
```
</pre
            >

            <pre v-if="page">
```galaxy
history_dataset_as_image(history_dataset_id=33b43b4e7093c91f)
```
</pre
            >
            <pre v-else>
```galaxy
history_dataset_as_image(output=normalized_result_plot)
```
</pre
            >

            <dl>
                <dt><tt>history_dataset_display</tt></dt>
                <dd>Embed a dataset description in the resulting document.</dd>
                <dt><tt>history_dataset_collection_display</tt></dt>
                <dd>Embed a dataset collection description in the resulting document.</dd>
                <dt><tt>history_dataset_as_image</tt></dt>
                <dd>
                    Embed a dataset as an image in the resulting document - the dataset should be an image datatype.
                </dd>
                <dt><tt>history_dataset_peek</tt></dt>
                <dd>
                    Embed Galaxy's metadata attribute 'peek' into the resulting document - this is datatype dependent
                    metadata but usually this is a few lines from the start of a file.
                </dd>
                <dt><tt>history_dataset_info</tt></dt>
                <dd>
                    Embed Galaxy's metadata attribute 'info' into the resulting document - this is datatype dependent
                    metadata but usually this is the program output that generated the dataset.
                </dd>
            </dl>

            <h3>Workflow Commands</h3>

            <p v-if="page">
                These commands reference a workflow by an object ID. The following example would display a
                representation of the workflow in the resulting Galaxy Page:
            </p>
            <p v-else>These commands reference the current workflow and do not require an input for the most part.</p>

            <pre v-if="page">
```galaxy
workflow_display(workflow_id=33b43b4e7093c91f>)
```
</pre
            >
            <pre v-else>
```galaxy
workflow_display()
```
            </pre>

            <dl>
                <dt><tt>workflow_display</tt></dt>
                <dd>Embed a description of the workflow itself in the resulting document.</dd>
            </dl>

            <h3>Job Commands</h3>

            <p v-if="page">
                These commands reference a Galaxy job. For instance, the following example would show the job parameters
                the job ID <tt>33b43b4e7093c91f</tt>.
            </p>
            <p v-else>
                These commands reference a Galaxy job or collection of jobs associated with a labeled step in the
                workflow. For instance, the following example would show the job parameters for the step with the label
                <tt>mapping</tt>.
            </p>

            <pre v-if="page">
```galaxy
job_parameters(job_id=33b43b4e7093c91f)
```
</pre
            >
            <pre v-else>
```galaxy
job_parameters(step=mapping)
```
            </pre>

            <dt><tt>tool_stderr</tt></dt>
            <dd>Embed the tool standard error stream for this job in the resulting document.</dd>
            <dt><tt>tool_stdout</tt></dt>
            <dd>Embed the tool standard output stream for this job in the resulting document.</dd>
            <dt><tt>job_metrics</tt></dt>
            <dd>
                Embed the job metrics for this job in the resulting document (if Galaxy is configured and you have
                permission).
            </dd>
            <dt><tt>job_parameters</tt></dt>
            <dd>Embed the tool parameters for this job in the resulting document.</dd>
        </div>
    </b-modal>
</template>
