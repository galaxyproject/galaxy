<template>
    <div>
        <GBreadcrumb v-if="dataManager && jobId && !loading" id="breadcrumb" :items="breadcrumbItems" />
        <GAlert :message="message" :variant="status" />
        <GAlert v-for="(error, index) in errorMessages" :key="index" :message="error" variant="error" />
        <GAlert v-if="viewOnly" message="Not implemented" variant="dark" />
        <GAlert v-else-if="loading" message="Waiting for data" variant="info" />
        <GContainer v-else-if="dataManager">
            <GRow>
                <GCol>
                    <GCard
                        id="data-manager-card"
                        header-bg-variant="primary"
                        header-text-variant="white"
                        border-variant="primary"
                        class="mb-3">
                        <template v-slot:header>
                            <GContainer>
                                <GRow align-v="center">
                                    <GCol cols="auto">
                                        <GButton v-b-tooltip.hover title="Rerun" :href="runUrl">
                                            <span class="fa fa-redo" />
                                        </GButton>
                                    </GCol>
                                    <GCol>
                                        <b>{{ dataManager["name"] }}</b> <i>{{ dataManager["description"] }}</i>
                                    </GCol>
                                </GRow>
                            </GContainer>
                        </template>
                        <GCard v-for="(hda, i) in hdaInfo" :id="'data-card-' + i" :key="i" class="mb-4">
                            <template v-slot:header>
                                <GTable :fields="fields" :items="[hda]" caption-top small stacked>
                                    <template v-slot:table-caption>
                                        <GContainer>
                                            <GRow align-v="center">
                                                <GCol cols="auto">
                                                    <GButton
                                                        v-b-tooltip.hover
                                                        title="View complete info"
                                                        :href="hdaInfo[i]['infoUrl']"
                                                        target="galaxy_main">
                                                        <span class="fa fa-info-circle" />
                                                    </GButton>
                                                </GCol>
                                                <GCol>
                                                    <b>{{ hda["name"] }}</b>
                                                </GCol>
                                            </GRow>
                                        </GContainer>
                                    </template>
                                </GTable>
                            </template>
                            <GTable
                                v-for="(output, j) in dataManagerOutput[i]"
                                :key="j"
                                :fields="outputFields(output[1][0])"
                                :items="output[1]"
                                small
                                stacked
                                hover
                                striped>
                                <template v-slot:table-caption>
                                    Data Table: <b>{{ output[0] }}</b>
                                </template>
                            </GTable>
                        </GCard>
                    </GCard>
                </GCol>
            </GRow>
        </GContainer>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

import { GAlert, GBreadcrumb, GButton, GCard, GCol, GContainer, GRow, GTable } from "@/component-library";

export default {
    components: {
        GAlert,
        GBreadcrumb,
        GButton,
        GCard,
        GCol,
        GContainer,
        GRow,
        GTable,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            jobId: Number,
            exitCode: Number,
            runUrl: "#",
            dataManager: [],
            hdaInfo: [],
            dataManagerOutput: [],
            errorMessages: [],
            fields: [
                { key: "created" },
                { key: "fileSize", label: "Filesize" },
                {
                    key: "fileName",
                    label: "Full path",
                    tdClass: "table-cell-break-word",
                },
            ],
            viewOnly: false,
            message: "",
            status: "",
            loading: true,
        };
    },
    computed: {
        breadcrumbItems() {
            return [
                {
                    text: "Data Managers",
                    to: { name: "DataManager" },
                },
                {
                    text: this.dataManager["name"] + " ( " + this.dataManager["description"] + " )",
                    href: this.dataManager["toolUrl"],
                    target: "_blank",
                },
                {
                    text: "Jobs",
                    to: {
                        name: "DataManagerJobs",
                        params: { id: this.dataManager["id"] },
                    },
                },
                {
                    text: "Job " + this.jobId,
                    active: true,
                },
            ];
        },
    },
    created() {
        axios
            .get(`${getAppRoot()}data_manager/job_info?id=${this.id}`)
            .then((response) => {
                this.jobId = response.data.jobId;
                this.exitCode = response.data.exitCode;
                this.runUrl = response.data.runUrl;
                this.dataManager = response.data.dataManager;
                this.hdaInfo = response.data.hdaInfo;
                this.dataManagerOutput = response.data.dataManagerOutput;
                this.errorMessages = response.data.errorMessages;
                this.viewOnly = response.data.viewOnly;
                this.message = response.data.message;
                this.status = response.data.status;
                this.loading = false;
            })
            .catch((error) => {
                console.error(error);
            });
    },
    methods: {
        outputFields(output) {
            return Object.keys(output).reduce((acc, c) => [...acc, { key: c, label: c }], []);
        },
    },
};
</script>

<style>
/* Can not be scoped because of table-cell-break-word tdClass */
.table-cell-break-word {
    word-break: break-word;
}
</style>
