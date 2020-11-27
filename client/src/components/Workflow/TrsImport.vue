<template>
    <div>
        <b-card v-if="!isAnonymous" title="GA4GH Tool Registry Server (TRS) Workflow Import">
            <b-alert :show="hasErrorMessage" variant="danger">{{ errorMessage }}</b-alert>
            <div>
                <b>TRS Server:</b>
                <TrsServerSelection
                    :query-trs-server="queryTrsServer"
                    :query-trs-id="queryTrsId"
                    @onTrsSelection="onTrsSelection"
                    @onError="onTrsSelectionError"
                />
            </div>
            <div v-if="isAutoImport && !hasErrorMessage" class="text-center my-2">
                <b-spinner class="align-middle"></b-spinner>
                <strong>Loading your Workflow...</strong>
            </div>
            <div v-else>
                <div>
                    <b>TRS ID:</b>
                    <b-form-input v-model="toolId" />
                </div>
                <trs-tool :trs-tool="trsTool" v-if="trsTool" @onImport="importVersion(trsTool.id, $event)" />
            </div>
        </b-card>
        <b-alert v-else show variant="danger" class="text-center my-2"
            >Anonymous user cannot import workflows, please register or log in</b-alert
        >
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";
import TrsMixin from "./trsMixin";
import { Toast } from "ui/toast";
import { getGalaxyInstance } from "app";

Vue.use(BootstrapVue);

export default {
    mixins: [TrsMixin],
    props: {
        queryTrsServer: {
            type: String,
            default: null,
        },
        queryTrsId: {
            type: String,
            default: null,
        },
        queryTrsVersionId: {
            type: String,
            default: null,
        },
        isRun: {
            type: Boolean,
            default: false,
        },
    },
    created() {
        this.services = new Services();
        this.toolId = this.queryTrsId;
    },
    data() {
        return {
            trsSelection: null,
            toolId: null,
            trsTool: null,
            errorMessage: null,
            isAutoImport: this.queryTrsVersionId && this.queryTrsServer && this.queryTrsId,
        };
    },
    computed: {
        hasErrorMessage() {
            return this.errorMessage != null;
        },
        isAnonymous() {
            return !getGalaxyInstance().user.isAnonymous();
        },
    },
    watch: {
        toolId: function () {
            this.onToolId();
        },
    },
    methods: {
        onTrsSelection(selection) {
            this.trsSelection = selection;
            if (this.toolId) {
                this.onToolId();
            }
        },
        onTrsSelectionError(message) {
            this.errorMessage = message;
        },
        onToolId() {
            if (!this.trsSelection) {
                return;
            }
            this.services
                .getTrsTool(this.trsSelection.id, this.toolId)
                .then((tool) => {
                    this.trsTool = tool;
                    this.errorMessage = null;
                    if (this.isAutoImport) {
                        const version = this.trsTool.versions.find((version) => version.id === this.queryTrsVersionId);
                        if (version) {
                            this.importVersion(this.trsTool.id, version, this.isRun);
                        } else {
                            Toast.warning(`Specified version: ${this.queryTrsVersionId} doesn't exist`);
                            this.isAutoImport = false;
                        }
                    }
                })
                .catch((errorMessage) => {
                    this.trsTool = null;
                    this.errorMessage = errorMessage;
                });
        },
    },
};
</script>
