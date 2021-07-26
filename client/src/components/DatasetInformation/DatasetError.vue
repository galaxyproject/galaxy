<template>
    <DatasetProvider :id="datasetId" v-slot="{ item: dataset, loading }">
        <div v-if="!loading">
            <JobDetailsProvider :jobid="dataset.creating_job" v-slot="{ result, loading }">
                <div v-if="!loading">
                    <div class="page-container edit-attr">
                        <div class="response-message"></div>
                    </div>
                    <h2>Dataset Error Report</h2>
                    <p>
                        An error occurred while running the tool <b>{{ result.tool_id }}</b
                        >.
                    </p>
                    <div v-if="result.tool_stderr || result.job_stderr || result.job_messages">
                        <h3>Details</h3>
                    </div>
                    <div v-if="result.job_messages">
                        <p>Execution resulted in the following messages:</p>
                        <div v-for="job_message in result.job_messages">
                            <pre class="rounded code">{{ job_message["desc"] }}</pre>
                        </div>
                    </div>
                    <div v-if="result.tool_stderr">
                        <p>Tool generated the following standard error:</p>
                        <pre class="rounded code">{{ result.tool_stderr }}</pre>
                    </div>
                    <div v-if="result.job_stderr">
                        <p>Galaxy job runner generated the following standard error:</p>
                        <pre class="rounded code">{{ result.job_stderr }}</pre>
                    </div>
                </div>
            </JobDetailsProvider>
            <JobProblemProvider :jobid="dataset.creating_job" v-slot="{ result, loading }">
                <h3 class="common_problems"></h3>
            </JobProblemProvider>
            <h3>Troubleshooting</h3>
            <p>
                There are a number of helpful resources to self diagnose and correct problems.
                <br />
                Start here:
                <b>
                    <a href="https://galaxyproject.org/support/tool-error/" target="_blank">
                        My job ended with an error. What can I do?
                    </a>
                </b>
            </p>
            <h3>Issue Report</h3>
        </div>
    </DatasetProvider>
</template>

<script>
import { DatasetProvider } from "components/WorkflowInvocationState/providers";
import { JobDetailsProvider, JobProblemProvider } from "components/providers/JobProvider";
import FormDisplay from "components/Form/FormDisplay";
import FormCard from "components/Form/FormCard";

export default {
    components: {
        DatasetProvider,
        FormDisplay,
        FormCard,
        JobDetailsProvider,
        JobProblemProvider,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
    data() {
        return {};
    },
    computed: {
        inputs() {
            return [];
        },
    },
    methods: {
        onChange(data) {},
    },
};
</script>
