<template>
    <div>
        <b-container class="mb-3">
            <b-row>
                <b-col md="6">
                    <h2>
                        <span id="jobs-title">Jobs</span>
                    </h2>
                </b-col>
                <b-col>
                    <job-lock />
                </b-col>
            </b-row>
        </b-container>
        <b-alert v-if="this.message !== ''" :variant="galaxyKwdToBootstrap(status)" show>
            {{ message }}
        </b-alert>
        <b-alert variant="info" show>
            <p>
                Unfinished and recently finished jobs are displayed on this page. The 'cutoff' input box will do two
                things -- it will limit the display of unfinished jobs to only those jobs that have not had their job
                state updated recently, and it will limit the recently finished jobs list to only displaying jobs that
                have finished since the cutoff.
            </p>
            If any jobs are displayed, you may choose to stop them. Your stop message will be displayed to the user as:
            "This job was stopped by an administrator: <strong>&lt;YOUR MESSAGE&gt;</strong> For more information or
            help, report this error".
        </b-alert>
        <b-alert v-if="loading" variant="info" show>
            Waiting for data
        </b-alert>
        <div v-else>
            <b-container class="mb-3">
                <b-row>
                    <b-col md="6">
                        <b-form name="jobs" @submit.prevent="onRefresh">
                            <b-form-group
                                id="cutoff"
                                label="Update Jobs"
                                label-for="cutoff-seconds"
                                description="Cutoff in seconds"
                            >
                                <b-input-group>
                                    <b-form-input id="cutoff" type="number" placeholder="180" v-model="cutoff">
                                    </b-form-input>
                                    <b-input-group-append>
                                        <b-btn type="submit">Refresh</b-btn>
                                    </b-input-group-append>
                                </b-input-group>
                            </b-form-group>
                        </b-form>
                    </b-col>
                </b-row>
                <b-row>
                    <b-col md="6">
                        <b-form-group
                            label="Filter Jobs"
                            label-for="filter-regex"
                            description="Search for strings or regular expressions"
                        >
                            <b-input-group id="filter-regex">
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
                    <b-col>
                        <b-card v-if="jobsItemsComputed.length" header="Stop Selected Jobs">
                            <b-form @submit.prevent="onStopJobs">
                                <b-form-group label-for="stop-message" description="will be displayed to the user">
                                    <b-input-group>
                                        <b-form-input
                                            id="stop-message"
                                            v-model="stopMessage"
                                            placeholder="Stop message"
                                            required
                                        >
                                        </b-form-input>
                                        <b-input-group-append>
                                            <b-btn type="submit">Submit</b-btn>
                                        </b-input-group-append>
                                    </b-input-group>
                                </b-form-group>
                            </b-form>
                        </b-card>
                    </b-col>
                </b-row>
            </b-container>
            <b-alert v-if="!jobsItemsComputed.length" variant="secondary" show>
                There are no unfinished jobs to show with current cutoff time.
            </b-alert>
            <b-table
                v-else
                :fields="jobsFieldsComputed"
                :items="jobsItemsComputed"
                v-model="jobsItemsModel"
                :filter="filter"
                hover
                responsive
                striped
                caption-top
                @row-clicked="showRowDetails"
                :busy="busy"
            >
                <template v-slot:table-caption>
                    Unfinished Jobs: These jobs are unfinished and have had their state updated in the previous
                    {{ cutoffDisplay }} seconds.
                </template>
                <template v-slot:head(selected)>
                    <b-form-checkbox
                        v-model="allSelected"
                        :indeterminate="indeterminate"
                        @change="toggleAll"
                    ></b-form-checkbox>
                </template>
                <template v-slot:cell(selected)="data">
                    <b-form-checkbox
                        v-model="selectedStopJobIds"
                        :checked="allSelected"
                        :key="data.index"
                        :value="data.item['id']"
                    ></b-form-checkbox>
                </template>
                <template v-slot:cell(job_info)="data">
                    <b-link :href="data.value.info_url" @click.prevent="clickJobInfo(data.value.id)">
                        {{ data.value.id }}
                    </b-link>
                </template>
                <template v-slot:row-details="row">
                    <job-details :command-line="row.item.command_line" :job-id="row.item.jobId" />
                </template>
            </b-table>
            <b-alert v-if="!recentJobsItemsComputed.length" variant="secondary" show>
                There are no recently finished jobs to show with current cutoff time.
            </b-alert>
            <b-table
                v-else
                :fields="recentJobsFieldsComputed"
                :items="recentJobsItemsComputed"
                :filter="filter"
                hover
                responsive
                striped
                caption-top
                @row-clicked="showRowDetails"
                :busy="busy"
            >
                <template v-slot:table-caption>
                    Recent Jobs: These jobs have completed in the previous {{ cutoffDisplay }} seconds.
                </template>
                <template v-slot:cell(job_info)="data">
                    <b-link :href="data.value.info_url" @click.prevent="clickJobInfo(data.value.id)">
                        {{ data.value.id }}
                    </b-link>
                </template>
                <template v-slot:cell(update_time)="data">
                    <utc-date :date="data.value" mode="elapsed" />
                </template>
                <template v-slot:row-details="row">
                    <job-details :command-line="row.item.command_line" :job-id="row.item.id" />
                </template>
            </b-table>
            <b-modal ref="job-info-modal" scrollable hide-header ok-only @hidden="resetModalContents">
                <div class="info-frame-container">
                    <iframe :src="selectedJobUrl"></iframe>
                </div>
            </b-modal>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import UtcDate from "components/UtcDate";
import axios from "axios";
import JobDetails from "./JobDetails";
import JobLock from "./JobLock";

function cancelJob(jobId, message) {
    const url = `${getAppRoot()}api/jobs/${jobId}`;
    return axios.delete(url, { data: { message: message } });
}

export default {
    components: { UtcDate, JobDetails, JobLock },
    data() {
        return {
            jobsItems: [],
            jobsItemsModel: [],
            recentJobsItems: [],
            jobsFields: [
                { key: "job_info", label: "Job ID", sortable: true },
                { key: "user" },
                { key: "tool_id", label: "Tool", tdClass: ["break-word"] },
                { key: "state" },
                { key: "job_runner_name", label: "Job Runner" },
                { key: "job_runner_external_id", label: "PID/Cluster ID", sortable: true },
            ],
            cutoff: 180,
            cutoffDisplay: 180,
            selectedStopJobIds: [],
            selectedJobId: null,
            allSelected: false,
            indeterminate: false,
            stopMessage: "",
            filter: "",
            message: "",
            status: "",
            loading: true,
            busy: true,
        };
    },
    watch: {
        selectedStopJobIds(newVal) {
            if (newVal.length === 0) {
                this.indeterminate = false;
                this.allSelected = false;
            } else if (newVal.length === this.jobsItemsModel.length) {
                this.indeterminate = false;
                this.allSelected = true;
            } else {
                this.indeterminate = true;
                this.allSelected = false;
            }
        },
    },
    methods: {
        update() {
            this.busy = true;
            let params = [];
            params.push(`cutoff=${this.cutoff}`);
            params = params.join("&");
            axios
                .get(`${getAppRoot()}admin/jobs_list?${params}`)
                .then((response) => {
                    this.jobsItems = response.data.jobs;
                    this.recentJobsItems = response.data.recent_jobs;
                    this.cutoffDisplay = response.data.cutoff;
                    this.message = response.data.message;
                    this.status = response.data.status;
                    this.loading = false;
                    this.busy = false;
                })
                .catch((error) => {
                    this.message = error.response.data.err_msg;
                    this.status = "error";
                    console.log(error.response);
                });
        },
        onRefresh() {
            this.update();
        },
        onStopJobs() {
            axios.all(this.selectedStopJobIds.map((jobId) => cancelJob(jobId, this.stopMessage))).then((res) => {
                this.update();
                this.selectedStopJobIds = [];
                this.stopMessage = "";
            });
        },
        clickJobInfo(id) {
            this.selectedJobId = id;
            this.$refs["job-info-modal"].show();
        },
        resetModalContents() {
            this.selectedJobId = null;
        },
        showRowDetails(row, index, e) {
            if (e.target.nodeName != "A") {
                row._showDetails = !row._showDetails;
            }
        },
        translateState(state) {
            const translateDict = {
                ok: "success",
                error: "danger",
                new: "primary",
                queued: "secondary",
                running: "info",
                upload: "dark",
            };
            return translateDict[state] || "primary";
        },
        computeItems(items) {
            return items.map((job) => {
                return {
                    ...job,
                    _showDetails: false,
                    _cellVariants: { state: this.translateState(job.state) },
                };
            });
        },
        computeFields(fields) {
            const f = Array.from(fields).slice(0);
            return f;
        },
        toggleAll(checked) {
            this.selectedStopJobIds = checked ? this.jobsItemsModel.reduce((acc, j) => [...acc, j["id"]], []) : [];
        },
        galaxyKwdToBootstrap(status) {
            let variant = "info";
            if (status !== "") {
                variant = status;
            }
            const galaxyKwdToBoostrapDict = {
                done: "success",
                info: "info",
                warning: "warning",
                error: "danger",
            };
            if (variant in galaxyKwdToBoostrapDict) {
                return galaxyKwdToBoostrapDict[variant];
            } else {
                return variant;
            }
        },
    },
    computed: {
        jobsItemsComputed() {
            return this.computeItems(this.jobsItems);
        },
        recentJobsItemsComputed() {
            return this.computeItems(this.recentJobsItems);
        },
        jobsFieldsComputed() {
            const f = this.jobsFields.slice(0);
            f.splice(0, 0, { key: "selected", label: "" });
            f.splice(2, 0, { key: "update_time", label: "Last Update", sortable: true });
            return this.computeFields(f);
        },
        recentJobsFieldsComputed() {
            const f = this.jobsFields.slice(0);
            f.splice(2, 0, { key: "update_time", label: "Finished", sortable: true });
            return this.computeFields(f);
        },
        selectedJobUrl() {
            return `${getAppRoot()}admin/job_info?jobid=${this.selectedJobId}`;
        },
    },
    created() {
        this.update();
    },
};
</script>

<style>
/* Can not be scoped because of command line tdClass */
.break-word {
    white-space: pre-wrap;
    word-break: break-word;
}
.info-frame-container {
    overflow: hidden;
    padding-top: 100%;
    position: relative;
}
.info-frame-container iframe {
    border: 0;
    height: 100%;
    left: 0;
    position: absolute;
    top: 0;
    width: 100%;
}
</style>
