<template>
    <div>
        <div v-if="toolStderr || jobStderr || hasMessages">
            <h3>Details</h3>
        </div>
        <div v-if="hasMessages" id="dataset-error-job-messages">
            <p>Execution resulted in the following messages:</p>
            <div v-for="(jobMessage, index) in jobMessages" :key="index">
                <pre class="rounded code">{{ jobMessage["desc"] }}</pre>
            </div>
        </div>
        <div v-if="toolStderr">
            <p>Tool generated the following standard error:</p>
            <pre id="dataset-error-tool-stderr" class="rounded code">{{ toolStderr }}</pre>
        </div>
        <div v-if="jobStderr">
            <p>Galaxy job runner generated the following standard error:</p>
            <pre id="dataset-error-job-stderr" class="rounded code">{{ jobStderr }}</pre>
        </div>
    </div>
</template>

<script>
import FormElement from "components/Form/FormElement";
import { DatasetProvider } from "components/WorkflowInvocationState/providers";
import { JobDetailsProvider, JobProblemProvider } from "components/providers/JobProvider";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug } from "@fortawesome/free-solid-svg-icons";
import { sendErrorReport } from "./services";

library.add(faBug);

export default {
    components: {
        DatasetProvider,
        FontAwesomeIcon,
        FormElement,
        JobDetailsProvider,
        JobProblemProvider,
    },
    props: {
        toolStderr: {
            type: String,
            required: true,
        },
        jobStderr: {
            type: String,
            required: true,
        },
        jobMessages: {
            type: Array,
            required: true,
        },
    },
    computed: {
        hasMessages() {
            return this.jobMessages && this.jobMessages.length > 0;
        },
    },
};
</script>
