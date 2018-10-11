<template>
    <div>
        <b-breadcrumb v-if="!loading" :items="breadcrumbItems" />
        <Alert :message="message" :variant="status" />
        <Alert v-for="(error, index) in errorMessages" :key="index" :message="error" variant="error" />
        <Alert v-if="viewOnly" message="Not implemented" variant="dark" />
        <Alert v-else-if="loading" message="Waiting for data" variant="info" />
        <b-container v-else>
            <b-row>
                <b-col>
                    <b-card header-bg-variant="primary" header-text-variant="white" border-variant="primary" class="mb-3" id="data-manager-card">
                        <template slot="header">
                            <b-container>
                                <b-row align-v="center">
                                    <b-col cols="auto">
                                        <b-button v-b-tooltip.hover title="Rerun" :href="runUrl">
                                            <span class="fa fa-refresh" />
                                        </b-button>
                                    </b-col>
                                    <b-col>
                                        <b>{{ dataManager["name"] }}</b>
                                        <i>{{ dataManager['description'] }}</i>
                                    </b-col>
                                </b-row>
                            </b-container>
                        </template>
                        <b-card v-for="(item, i) in tableItems" :key="i" class="mb-4" id="data-card">
                            <template slot="header">
                                <b-table :fields="fields" :items="[item]" caption-top small stacked>
                                    <template slot="table-caption">
                                        <b-container>
                                            <b-row align-v="center">
                                                <b-col cols="auto">
                                                    <b-button v-b-tooltip.hover title="View complete info" :href="tableItems[i]['infoUrl']" target="galaxy_main">
                                                        <span class="fa fa-info-circle" />
                                                    </b-button>
                                                </b-col>
                                                <b-col>
                                                    <b>{{ item["name"] }}</b>
                                                </b-col>
                                            </b-row>
                                        </b-container>
                                    </template>
                                </b-table>
                            </template>
                            <b-table v-for="(output, j) in dataManagerOutput[i]" :key="j" :fields="outputFields(output[1])" :items="output[1]" small stacked hover striped>
                                <template slot="table-caption">
                                    Data Table:
                                    <b>{{ output[0] }}</b>
                                </template>
                            </b-table>
                        </b-card>
                    </b-card>
                </b-col>
            </b-row>
        </b-container>
    </div>
</template>

<script>
import axios from "axios";
import Alert from "components/Alert.vue";

export default {
    components: {
        Alert
    },
    props: {
        id: {
            type: String,
            required: true
        }
    },
    data() {
        return {
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
                    tdClass: "table-cell-break-word"
                }
            ],
            viewOnly: false,
            message: "",
            status: "",
            loading: true
        };
    },
    computed: {
        breadcrumbItems() {
            return [
                {
                    text: "Data Managers",
                    to: "/"
                },
                {
                    text: this.dataManager["name"] + " ( " + this.dataManager["description"] + " )",
                    href: this.dataManager["toolUrl"],
                    target: "_blank"
                },
                {
                    text: "Jobs",
                    to: {
                        name: "DataManagerJobs",
                        params: { id: this.dataManager["id"] }
                    }
                },
                {
                    text: "Job " + this.jobId,
                    active: true
                }
            ];
        },
        tableItems() {
            let tableItems = this.hdaInfo;
            return tableItems;
        }
    },
    methods: {
        outputFields(output) {
            let outputFields = [];
            for (const k of Object.keys(output[0])) {
                outputFields.push({ key: k, label: k });
            }
            return outputFields;
        }
    },
    created() {
        axios
            .get(`${Galaxy.root}data_manager/job_info?id=${this.id}`)
            .then(response => {
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
            .catch(error => {
                console.error(error);
            });
    }
};
</script>

<style>
.table-cell-break-word {
    word-break: break-word;
}
</style>
