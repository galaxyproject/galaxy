<template>
    <div>
        <b-alert v-if="errorMessage" variant="danger" show>
            <h2 class="alert-heading h-sm">Failed to access Dataset details.</h2>
            {{ errorMessage }}
        </b-alert>
        <DatasetProvider :id="datasetId" v-slot="{ result: dataset, loading: datasetLoading }">
            <JobDetailsProvider
                v-if="!datasetLoading"
                v-slot="{ result: jobDetails, loading }"
                :job-id="dataset.creating_job"
                @error="onError">
                <div v-if="!loading">
                    <SelfReportingError
                        :result-messages="resultMessages"
                        :show-form="showForm"
                        :message="message"
                        :submit="submit"
                        :dataset="dataset"
                        :command-outputs="buildCommandOutputs(jobDetails)"
                        :notifications="buildNotifications(jobDetails.tool_id)" />
                </div>
            </JobDetailsProvider>
        </DatasetProvider>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug } from "@fortawesome/free-solid-svg-icons";
import { DatasetProvider } from "components/providers";
import { JobDetailsProvider } from "components/providers/JobProvider";
import { mapState } from "pinia";

import { useMarkdown } from "@/composables/markdown";
import { useUserStore } from "@/stores/userStore";

import { sendErrorReport } from "./services";

import SelfReportingError from "../Common/SelfReportingError.vue";

library.add(faBug);

export default {
    components: {
        DatasetProvider,
        JobDetailsProvider,
        SelfReportingError,
    },
    props: {
        datasetId: {
            type: String,
            required: true,
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
    },
    methods: {
        onError(err) {
            this.errorMessage = err;
        },
        buildNotifications(toolId) {
            return [
                {
                    text: `An error occurred while running the tool <b id='dataset-error-tool-id' class='text-break  '>${toolId}</b>.`,
                },
            ];
        },
        buildCommandOutputs(details) {
            return [
                {
                    text: "Execution resulted in the following messages:",
                    detail: details.job_messages,
                },
                {
                    text: "Tool generated the following standard error:",
                    detail: [details.tool_stderr],
                },
                {
                    text: "Galaxy job runner generated the following standard error:",
                    detail: [details.job_stderr],
                },
            ];
        },
        submit(dataset, userEmailJob) {
            const email = userEmailJob || this.currentUserEmail;
            const message = this.message;
            sendErrorReport(dataset, message, email).then(
                (resultMessages) => {
                    this.resultMessages = resultMessages;
                },
                (errorMessage) => {
                    this.errorMessage = errorMessage;
                }
            );
        },
    },
};
</script>
