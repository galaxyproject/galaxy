<template>
    <div>
        <GBreadcrumb v-if="dataManager && !loading" id="breadcrumb" :items="breadcrumbItems" />
        <GAlert :message="message" :variant="status" />
        <GAlert v-if="viewOnly" message="Not implemented" variant="dark" />
        <GAlert v-else-if="loading" message="Waiting for data" variant="info" />
        <GAlert v-else-if="jobs && !jobs.length" message="There are no jobs for this data manager." variant="primary" />
        <div v-else-if="jobs">
            <GContainer fluid class="mb-3">
                <GRow>
                    <GCol md="6">
                        <GFormGroup description="Search for strings or regular expressions">
                            <GInputGroup>
                                <GInput v-model="filter" placeholder="Type to Search" @keyup.esc.native="filter = ''" />
                                <GInputGroupAppend>
                                    <GButton :disabled="!filter" @click="filter = ''">Clear (esc)</GButton>
                                </GInputGroupAppend>
                            </GInputGroup>
                        </GFormGroup>
                    </GCol>
                </GRow>
                <GRow>
                    <GCol>
                        <GButton :pressed.sync="showCommandLine" variant="outline-secondary">
                            {{ showCommandLine ? "Hide" : "Show" }} Command Line
                        </GButton>
                    </GCol>
                </GRow>
            </GContainer>
            <GTable id="jobs-table" :fields="tableFields" :filter="filter" :items="tableItems" hover responsive striped>
                <template v-slot:cell(actions)="row">
                    <GButtonGroup>
                        <GButton v-b-tooltip.hover title="Rerun" target="_top" :href="jobs[row.index]['runUrl']">
                            <span class="fa fa-redo" />
                        </GButton>
                        <GButton
                            :id="'job-' + jobs[row.index]['encId']"
                            v-b-tooltip.hover
                            title="View Info"
                            :to="{ name: 'DataManagerJob', params: { id: jobs[row.index]['encId'] } }">
                            <span class="fa fa-info-circle" />
                        </GButton>
                        <GButton
                            v-if="!showCommandLine"
                            :pressed.sync="row.detailsShowing"
                            @click.stop="row.toggleDetails()">
                            {{ row.detailsShowing ? "Hide" : "Show" }} Command Line
                        </GButton>
                    </GButtonGroup>
                </template>
                <template v-slot:row-details="row">
                    <GCard>
                        <h2 class="h-text">Command Line</h2>
                        <pre class="code"><code class="command-line">{{ row.item.commandLine }}</code></pre>
                        <template v-slot:footer>
                            <GButton class="mt-3" @click="row.toggleDetails">Hide Info</GButton>
                        </template>
                    </GCard>
                </template>
            </GTable>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

import {
    GAlert,
    GBreadcrumb,
    GButton,
    GButtonGroup,
    GCard,
    GCol,
    GContainer,
    GFormGroup,
    GInput,
    GInputGroup,
    GInputGroupAppend,
    GRow,
    GTable,
} from "@/component-library";

export default {
    components: {
        GAlert,
        GButton,
        GBreadcrumb,
        GButtonGroup,
        GCard,
        GCol,
        GContainer,
        GFormGroup,
        GInput,
        GInputGroup,
        GInputGroupAppend,
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
            dataManager: [],
            jobs: [],
            fields: [
                { key: "id", label: "Job ID", sortable: true },
                { key: "user" },
                { key: "updateTime", label: "Last Update", sortable: true },
                { key: "state" },
                { key: "actions" },
                { key: "jobRunnerName", label: "Job Runner" },
                { key: "jobRunnerExternalId", label: "PID/Cluster ID", sortable: true },
            ],
            showCommandLine: true,
            filter: "",
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
                    active: true,
                },
            ];
        },
        tableFields() {
            const tableFields = this.fields.slice(0);
            if (this.showCommandLine) {
                tableFields.splice(5, 0, {
                    key: "commandLine",
                    tdClass: ["code", "command-line"],
                });
            }
            return tableFields;
        },
        tableItems() {
            const tableItems = this.jobs.slice(0);

            for (const item of tableItems) {
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
        },
    },
    created() {
        axios
            .get(`${getAppRoot()}data_manager/jobs_list?id=${decodeURIComponent(this.id)}`)
            .then((response) => {
                this.dataManager = response.data.dataManager;
                this.jobs = response.data.jobs;
                this.viewOnly = response.data.viewOnly;
                this.message = response.data.message;
                this.status = response.data.status;
                this.loading = false;
            })
            .catch((error) => {
                console.error(error);
            });
    },
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
