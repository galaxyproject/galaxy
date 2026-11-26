<template>
    <div>
        <BBreadcrumb v-if="dataManager && jobId && !loading" id="breadcrumb" :items="breadcrumbItems" />

        <GAlert v-if="message" :variant="statusVariant">{{ message }}</GAlert>

        <GAlert v-for="(error, index) in errorMessages" :key="index" variant="danger">{{ error }}</GAlert>

        <GAlert v-if="viewOnly" variant="dark">Not implemented</GAlert>
        <GAlert v-else-if="loading" variant="info">Waiting for data</GAlert>
        <BContainer v-else-if="dataManager">
            <BRow>
                <BCol>
                    <BCard
                        id="data-manager-card"
                        header-bg-variant="primary"
                        header-text-variant="white"
                        border-variant="primary"
                        class="mb-3">
                        <template v-slot:header>
                            <BContainer>
                                <BRow align-v="center">
                                    <BCol cols="auto">
                                        <GButton tooltip title="Rerun" :href="runUrl">
                                            <!-- <span class="fa fa-redo" /> -->
                                            <FontAwesomeIcon :icon="faRedo" />
                                        </GButton>
                                    </BCol>

                                    <BCol>
                                        <b>{{ dataManager["name"] }}</b> <i>{{ dataManager["description"] }}</i>
                                    </BCol>
                                </BRow>
                            </BContainer>
                        </template>

                        <BCard v-for="(hda, i) in hdaInfo" :id="'data-card-' + i" :key="i" class="mb-4">
                            <template v-slot:header>
                                <GTable :fields="fields" :items="[hda]" caption-top compact stacked>
                                    <template v-slot:table-caption>
                                        <BContainer>
                                            <BRow align-v="center">
                                                <BCol cols="auto">
                                                    <GButton
                                                        tooltip
                                                        title="View complete info"
                                                        :to="`/datasets/${hdaInfo[i]['encId']}/show_params`">
                                                        <FontAwesomeIcon :icon="faInfoCircle" />
                                                    </GButton>
                                                </BCol>

                                                <BCol>
                                                    <b>{{ hda["name"] }}</b>
                                                </BCol>
                                            </BRow>
                                        </BContainer>
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
                        </BCard>
                    </BCard>
                </BCol>
            </BRow>
        </BContainer>
    </div>
</template>

<script>
import { faInfoCircle, faRedo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BBreadcrumb, BCard, BCol, BContainer, BRow } from "bootstrap-vue";

import { getAppRoot } from "@/onload/loadConfig";
import { alertVariant } from "@/utils/alertVariant";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GTable from "@/components/Common/GTable.vue";

export default {
    components: {
        BBreadcrumb,
        BCard,
        BCol,
        BContainer,
        BRow,
        FontAwesomeIcon,
        GAlert,
        GButton,
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
            faInfoCircle,
            faRedo,
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
        statusVariant() {
            return alertVariant(this.status);
        },
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
