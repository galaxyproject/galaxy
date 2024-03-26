<template>
    <div>
        <div class="page-container edit-attr">
            <div class="response-message"></div>
        </div>
        <h3 class="h-lg">Dataset Error Report</h3>
        <p v-if="notifications && !notifications.variant" v-html="notifications[0].text" />
        <span v-else-if="notifications && notifications.variant">
            <BAlert :variant="notifications.variant">
                <span v-html="notifications[0].text" />
            </BAlert>
        </span>
        <div v-if="hasDetails(commandOutputs)">
            <h4 class="h-md">Details</h4>
            <div v-for="(commandOutput, index) in commandOutputs" :key="index">
                <div v-if="hasMessages(commandOutput.detail)">
                    <p class="mt-3 mb-1">{{ commandOutput.text }}</p>
                    <div v-for="(value, index) in commandOutput.detail" :key="index">
                        <pre class="rounded code">{{ value }}</pre>
                    </div>
                </div>
            </div>
        </div>
        <JobProblemProvider v-slot="{ result: jobProblems }" :job-id="dataset.creating_job" @error="onError">
            <div v-if="jobProblems && (jobProblems.has_duplicate_inputs || jobProblems.has_empty_inputs)">
                <h4 class="common_problems mt-3 h-md">Detected Common Potential Problems</h4>
                <p v-if="jobProblems.has_empty_inputs" id="dataset-error-has-empty-inputs">
                    The tool was started with one or more empty input datasets. This frequently results in tool errors
                    due to problematic input choices.
                </p>
                <p v-if="jobProblems.has_duplicate_inputs" id="dataset-error-has-duplicate-inputs">
                    The tool was started with one or more duplicate input datasets. This frequently results in tool
                    errors due to problematic input choices.
                </p>
            </div>
        </JobProblemProvider>
        <h4 class="mt-3 h-md">Troubleshooting</h4>
        <p>
            There are a number of helpful resources to self diagnose and correct problems.
            <br />
            Start here:
            <b>
                <a
                    href="https://training.galaxyproject.org/training-material/faqs/galaxy/analysis_troubleshooting.html"
                    target="_blank">
                    My job ended with an error. What can I do?
                </a>
            </b>
        </p>
        <h4 class="mb-3 h-md">Issue Report</h4>
        <BAlert v-for="(resultMessage, index) in resultMessages" :key="index" :variant="resultMessage[1]" show>
            <span v-html="renderMarkdown(resultMessage[0])"></span>
        </BAlert>
        <div v-if="showForm" id="fieldsAndButton">
            <span class="mr-2 font-weight-bold">{{ "Your email address" | l }}</span>
            <span v-if="!!currentUser?.email">{{ currentUser?.email }}</span>
            <span v-else>{{ "You must be logged in to receive emails" | l }}</span>
            <FormElement
                id="dataset-error-message"
                v-model="message"
                :area="true"
                title="Please provide detailed information on the activities leading to this issue:" />
            <b-button
                id="dataset-error-submit"
                variant="primary"
                class="mt-3"
                :disabled="disableSubmit"
                @click="submit(dataset, currentUser?.email)">
                <FontAwesomeIcon icon="bug" class="mr-1" />Report
            </b-button>
        </div>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import FormElement from "components/Form/FormElement";
import { JobProblemProvider } from "components/providers/JobProvider";
import { mapState } from "pinia";

import { getGalaxyInstance } from "@/app";
import { useMarkdown } from "@/composables/markdown";
import { useUserStore } from "@/stores/userStore";

import { sendErrorReport } from "../DatasetInformation/services";

export default {
    components: {
        FontAwesomeIcon,
        FormElement,
        JobProblemProvider,
        BAlert,
    },
    props: {
        dataset: {
            type: Object,
            required: true,
        },
        commandOutputs: {
            type: Array,
            default: () => [],
        },
        notifications: {
            type: Array,
            default: () => [],
        },
    },
    setup() {
        const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });
        return { renderMarkdown };
    },
    data() {
        return {
            message: null,
            errorMessage: null,
            resultMessages: [],
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        showForm() {
            const noResult = !this.resultMessages.length;
            const hasError = this.resultMessages.some((msg) => msg[1] === "danger");
            return noResult || hasError;
        },
        disableSubmit() {
            const isEmailActive = !getGalaxyInstance().config.show_inactivity_warning;
            return !this.currentUser?.email || !isEmailActive;
        },
    },
    methods: {
        onError(err) {
            this.errorMessage = err;
        },
        submit(dataset, email) {
            sendErrorReport(dataset, this.message, email).then(
                (resultMessages) => {
                    this.resultMessages = resultMessages;
                },
                (errorMessage) => {
                    this.errorMessage = errorMessage;
                }
            );
        },
        hasDetails(outputs) {
            return (
                outputs
                    .map(({ detail }) => detail)
                    .flat(Infinity)
                    .filter((item) => item.length > 0).length > 0
            );
        },
        hasMessages(output) {
            return output.filter((item) => item.length > 0).length > 0;
        },
    },
};
</script>
