<template>
    <div v-if="currentUser && currentHistoryId">
        <b-alert :show="messageObj.message && messageObj.topLevel" :variant="messageObj.variant">
            {{ messageObj.message }}
        </b-alert>

        <LoadingSpan v-if="showLoading" message="Loading Tool" />

        <b-modal v-model="showErrorDialog" size="sm" :title="errorObj.title | l" scrollable ok-only>
            <b-alert v-if="errorObj.message" show variant="danger">
                {{ errorObj.message }}
            </b-alert>
            <b-alert show variant="warning">
                The server could not complete this request. Please verify your parameter settings, retry submission and
                contact the Galaxy Team if this error persists. A transcript of the submitted data is shown below.
            </b-alert>
            <small v-if="errorObj.content" class="text-muted">
                <pre>{{ errorContentPretty }}</pre>
            </small>
        </b-modal>

        <ToolTypeChooser
            :tool-config="toolConfig"
            :show-tool="showTool"
            :disable-tool="disableTool"
            :loading="loading"
            @onChangeVersion="onChangeVersion"
            @onSetError="onSetError">
            <template v-slot:tool-messages>
                <FormMessage v-if="!errorObj.dialog" variant="danger" :message="errorObj.message" :persistent="true" />
                <FormMessage v-if="!messageObj.topLevel" :variant="messageObj.variant" :message="messageObj.message" />
            </template>
        </ToolTypeChooser>
    </div>
</template>

<script>
import FormMessage from "components/Form/FormMessage";
import LoadingSpan from "components/LoadingSpan";
import { mapState } from "pinia";
import { useHistoryStore } from "stores/historyStore";
import { useUserStore } from "stores/userStore";

import { getToolFormData } from "./services";

import ToolTypeChooser from "./ToolTypeChooser.vue";

export default {
    components: {
        LoadingSpan,
        FormMessage,
        ToolTypeChooser,
    },
    props: {
        id: {
            type: String,
            default: null,
        },
        version: {
            type: String,
            default: null,
        },
        job_id: {
            type: String,
            default: null,
        },
        history_id: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            disableTool: false,
            loading: false,
            showLoading: true,
            showTool: false,
            showErrorDialog: false,
            toolConfig: {},
            messageObj: this.getDefaultMessageObj(),
            errorObj: this.getDefaultErrorObj(),
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useHistoryStore, ["currentHistoryId"]),
        errorContentPretty() {
            return JSON.stringify(this.errorObj.content, null, 4);
        },
    },
    watch: {
        toolConfig() {
            this.onSetError(null);
        },
        showErrorDialog(showErrorDialog) {
            if (!showErrorDialog) {
                this.onSetError(null);
            }
        },
    },
    created() {
        this.requestTool(this.version);
    },
    methods: {
        getDefaultMessageObj() {
            return {
                topLevel: false,
                variant: "info",
                message: null,
            };
        },
        getDefaultErrorObj() {
            return {
                dialog: false,
                message: null,
                title: null,
                content: null,
            };
        },
        onChangeVersion(newVersion) {
            this.requestTool(newVersion);
        },
        onSetMessage(messageObj) {
            this.messageObj = this.getDefaultMessageObj();
            if (messageObj) {
                this.messageObj = { ...this.messageObj, ...messageObj };
            }
        },
        onSetError(errorObj) {
            this.errorObj = this.getDefaultErrorObj();
            if (errorObj) {
                this.errorObj = { ...this.errorObj, ...errorObj };
            }
            this.showErrorDialog = this.errorObj.dialog;
        },
        requestTool(version) {
            this.disableTool = true;
            this.loading = true;
            console.debug("ToolPanel - Requesting tool.", this.id);

            return getToolFormData(this.id, version, this.job_id, this.history_id)
                .then((data) => {
                    this.toolConfig = data;
                    this.showTool = true;

                    if (version) {
                        this.onSetMessage({
                            topLevel: false,
                            variant: "success",
                            message: `Now you are using '${data.name}' version ${data.version}, id '${data.id}'.`,
                        });
                    } else {
                        this.onSetMessage(null);
                    }
                })
                .catch((error) => {
                    this.showTool = false;

                    this.onSetMessage({
                        topLevel: true,
                        variant: "danger",
                        message: `Loading tool ${this.id} failed: ${error}`,
                    });
                })
                .finally(() => {
                    this.disableTool = false;
                    this.loading = false;
                    this.showLoading = false;
                });
        },
    },
};
</script>
