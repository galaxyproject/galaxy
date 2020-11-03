<template>
    <b-card title="GA4GH Tool Registry Server (TRS) Workflow Import">
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
        <div>
            <b>TRS ID:</b>
            <b-form-input v-model="toolId" />
        </div>

        <trs-tool :trs-tool="trsTool" v-if="trsTool" @onImport="importVersion(trsTool.id, $event)" />
    </b-card>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services";
import TrsMixin from "./trsMixin";

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
        };
    },
    computed: {
        hasErrorMessage() {
            return this.errorMessage != null;
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
                    const version = this.trsTool.versions.find((version) => version.id === this.queryTrsVersionId);
                    if (version) {
                        this.importVersion(this.trsTool.id, version, this.isRun);
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
