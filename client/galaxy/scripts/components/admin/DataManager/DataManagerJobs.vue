<template>
    <div>
        <b-breadcrumb v-if="dataManager && !loading" :items="breadcrumbItems" id="breadcrumb" />
        <Alert :message="message" :variant="status" />
        <Alert v-if="viewOnly" message="Not implemented" variant="dark" />
        <Alert v-else-if="loading" message="Waiting for data" variant="info" />
        <Alert v-else-if="jobs && !jobs.length" message="There are no jobs for this data manager." variant="primary" />
        <div v-else-if="jobs">
            <b-container fluid class="mb-3">
                <b-row>
                    <b-col md="6">
                        <b-form-group description="Search for strings or regular expressions">
                            <b-input-group>
                                <b-form-input
                                    v-model="filter"
                                    placeholder="Type to Search"
                                    @keyup.esc.native="filter = ''"
                                />
                                <b-input-group-append>
                                    <b-btn :disabled="!filter" @click="filter = ''">Clear (esc)</b-btn>
                                </b-input-group-append>
                            </b-input-group>
                        </b-form-group>
                    </b-col>
                </b-row>
                <b-row>
                    <b-col>
                        <b-button :pressed.sync="showCommandLine" variant="outline-secondary">
                            {{ showCommandLine ? "Hide" : "Show" }} Command Line
                        </b-button>
                    </b-col>
                </b-row>
            </b-container>
            <b-table
                :fields="tableFields"
                :items="tableItems"
                :filter="filter"
                hover
                responsive
                striped
                id="jobs-table"
            >
                <!-- Enable cell formatting for the command line column -->
                <span slot="html" slot-scope="data" v-html="data.value"> </span>
                <template slot="actions" slot-scope="row">
                    <b-button-group>
                        <b-button v-b-tooltip.hover title="Rerun" target="_top" :href="jobs[row.index]['runUrl']">
                            <span class="fa fa-refresh" />
                        </b-button>
                        <b-button
                            v-b-tooltip.hover
                            title="View Info"
                            :to="{ name: 'DataManagerJob', params: { id: jobs[row.index]['encId'] } }"
                            :id="'job-' + jobs[row.index]['encId']"
                        >
                            <span class="fa fa-info-circle" />
                        </b-button>
                        <b-button
                            v-if="!showCommandLine"
                            @click.stop="row.toggleDetails()"
                            :pressed.sync="row.detailsShowing"
                        >
                            {{ row.detailsShowing ? "Hide" : "Show" }} Command Line
                        </b-button>
                    </b-button-group>
                </template>
                <template slot="row-details" slot-scope="row">
                    <b-card>
                        <h5>Command Line</h5>
                        <pre class="code"><code class="command-line">{{ row.item.commandLine }}</code></pre>
                        <template slot="footer">
                            <b-button class="mt-3" @click="row.toggleDetails">Hide Info</b-button>
                        </template>
                    </b-card>
                </template>
            </b-table>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
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
            dataManager: [],
            jobs: [],
            fields: [
                { key: "id", label: "Job ID", sortable: true },
                { key: "user" },
                { key: "updateTime", label: "Last Update", sortable: true },
                { key: "state" },
                { key: "actions" },
                { key: "jobRunnerName", label: "Job Runner" },
                { key: "jobRunnerExternalId", label: "PID/Cluster ID", sortable: true }
            ],
            showCommandLine: true,
            filter: "",
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
                    active: true
                }
            ];
        },
        tableFields() {
            let tableFields = this.fields.slice(0);
            if (this.showCommandLine) {
                tableFields.splice(5, 0, {
                    key: "commandLine",
                    tdClass: ["code", "command-line"]
                });
            }
            return tableFields;
        },
        tableItems() {
            let tableItems = this.jobs.slice(0);

            for (let item of tableItems) {
                // Nicer time formatting
                item["updateTime"] = item["updateTime"].replace("T", "\n");

                // Color state cells accordingly
                switch (item["state"]) {
                    case "ok":
                        item["_cellVariants"] = { state: "success" };
                        break;
                    case "error":
                        item["_cellVariants"] = { state: "danger" };
                        break;
                    case "deleted":
                        item["_cellVariants"] = { state: "warning" };
                        break;
                    case "running":
                        item["_cellVariants"] = { state: "info" };
                        break;
                    case "waiting":
                    case "queued":
                        item["_cellVariants"] = { state: "primary" };
                        break;
                    case "paused":
                        item["_cellVariants"] = { state: "secondary" };
                        break;
                }
            }
            return tableItems;
        }
    },
    created() {
        axios
            .get(`${getAppRoot()}data_manager/jobs_list?id=${decodeURIComponent(this.id)}`)
            .then(response => {
                this.dataManager = response.data.dataManager;
                this.jobs = response.data.jobs;
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
/* Can not be scoped because of command line tdClass */
.code {
    background: black;
    color: white;
    padding: 1em;
}
.command-line {
    white-space: pre-wrap;
    word-break: break-word;
}
</style>
