<template>
    <div aria-labelledby="jobs-title">
        <h1 id="jobs-title" class="h-lg">Jobs</h1>
        <b-alert v-if="message" :variant="status" show>
            {{ message }}
        </b-alert>
        <Heading h2 size="md" separator>Job Lock</Heading>
        <job-lock />
        <Heading h2 size="md" separator>Job Overview</Heading>
        <p>
            Below unfinished jobs are displayed (in the 'new', 'queued', 'running', or 'upload' states) and recently
            completed jobs (in 'error' or 'ok' states).
        </p>
        <p>
            You may choose to stop some of the displayed jobs and provide the user with a message. Your stop message
            will be displayed to the user as: "This job was stopped by an administrator:
            <strong>&lt;YOUR MESSAGE&gt;</strong>
            For more information or help, report this error".
        </p>
        <b-row>
            <b-col class="col-sm-4">
                <b-form-group description="Select whether or not to use the cutoff below.">
                    <b-form-checkbox id="show-all-running" v-model="showAllRunning" switch size="lg" @change="update">
                        {{ showAllRunning ? "Showing all unfinished jobs" : "Time cutoff applied to query" }}
                    </b-form-checkbox>
                </b-form-group>
                <b-form name="jobs" @submit.prevent="onRefresh">
                    <b-form-group
                        v-show="!showAllRunning"
                        id="cutoff"
                        label="Cutoff in minutes"
                        description="Display jobs that had their state updated in the given time period.">
                        <b-input-group>
                            <b-form-input id="cutoff" v-model="cutoffMin" type="number"> </b-form-input>
                        </b-input-group>
                    </b-form-group>
                </b-form>
                <b-form-group description="Use strings or regular expressions to search jobs.">
                    <b-input-group id="filter-regex">
                        <b-form-input v-model="filter" placeholder="Type to Search" @keyup.esc.native="filter = ''" />
                    </b-input-group>
                </b-form-group>
            </b-col>
        </b-row>
        <transition name="fade">
            <b-form v-if="unfinishedJobs.length && selectedStopJobIds.length" @submit.prevent="onStopJobs">
                <b-form-group label="Stop Selected Jobs" description="Stop message will be displayed to the user">
                    <b-input-group>
                        <b-form-input id="stop-message" v-model="stopMessage" placeholder="Stop message" required>
                        </b-form-input>
                        <b-input-group-append>
                            <b-btn type="submit">Submit</b-btn>
                        </b-input-group-append>
                    </b-input-group>
                </b-form-group>
            </b-form>
        </transition>
        <h3 class="mb-0 h-sm">Unfinished Jobs</h3>
        <jobs-table
            v-model="jobsItemsModel"
            :fields="unfinishedJobFields"
            :items="unfinishedJobs"
            :filter="filter"
            :table-caption="runningTableCaption"
            :no-items-message="runningNoJobsMessage"
            :loading="loading"
            :busy="busy">
            <template v-slot:head(selected)>
                <b-form-checkbox
                    v-model="allSelected"
                    :indeterminate="indeterminate"
                    @change="toggleAll"></b-form-checkbox>
            </template>
            <template v-slot:cell(selected)="data">
                <b-form-checkbox
                    :key="data.index"
                    v-model="selectedStopJobIds"
                    :checked="allSelected"
                    :value="data.item['id']"></b-form-checkbox>
            </template>
        </jobs-table>

        <template v-if="!showAllRunning">
            <h3 class="mb-0 h-sm">Finished Jobs</h3>
            <jobs-table
                :table-caption="finishedTableCaption"
                :fields="finishedJobFields"
                :items="finishedJobs"
                :filter="filter"
                :no-items-message="finishedNoJobsMessage"
                :loading="loading"
                :busy="busy">
            </jobs-table>
        </template>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import JobsTable from "components/admin/JobsTable";
import JobLock from "./JobLock";
import JOB_STATES_MODEL from "utils/job-states-model";
import { commonJobFields } from "./JobFields";
import { errorMessageAsString } from "utils/simple-error";
import { jobsProvider } from "components/providers/JobProvider";
import Heading from "components/Common/Heading";

function cancelJob(jobId, message) {
    const url = `${getAppRoot()}api/jobs/${jobId}`;
    return axios.delete(url, { data: { message: message } });
}

export default {
    components: { JobLock, JobsTable, Heading },
    data() {
        return {
            jobs: [],
            finishedJobs: [],
            unfinishedJobs: [],
            jobsItemsModel: [],
            finishedJobFields: [...commonJobFields, { key: "update_time", label: "Finished", sortable: true }],
            unfinishedJobFields: [
                { key: "selected", label: "" },
                ...commonJobFields,
                { key: "update_time", label: "Last Update", sortable: true },
            ],
            selectedStopJobIds: [],
            selectedJobId: null,
            allSelected: false,
            indeterminate: false,
            stopMessage: "",
            filter: "",
            message: "",
            status: "info",
            loading: true,
            busy: true,
            cutoffMin: 5,
            showAllRunning: false,
        };
    },
    computed: {
        finishedTableCaption() {
            return `These jobs have completed in the previous ${this.cutoffMin} minutes.`;
        },
        runningTableCaption() {
            return `These jobs are unfinished and have had their state updated in the previous ${this.cutoffMin} minutes. For currently running jobs, the "Last Update" column should indicate the runtime so far.`;
        },
        finishedNoJobsMessage() {
            return `There are no recently finished jobs to show with current cutoff time of ${this.cutoffMin} minutes.`;
        },
        runningNoJobsMessage() {
            let message = `There are no unfinished jobs`;
            if (!this.showAllRunning) {
                message += ` to show with current cutoff time of ${this.cutoffMin} minutes`;
            }
            message += ".";
            return message;
        },
    },
    watch: {
        filter(newVal) {
            this.update();
        },
        cutoffMin(newVal) {
            this.update();
        },
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
        jobs(newVal) {
            const unfinishedJobs = [];
            const finishedJobs = [];
            newVal.forEach((item) => {
                if (JOB_STATES_MODEL.NON_TERMINAL_STATES.includes(item.state)) {
                    unfinishedJobs.push(item);
                } else {
                    finishedJobs.push(item);
                }
            });
            this.unfinishedJobs = unfinishedJobs;
            this.finishedJobs = finishedJobs;
        },
    },
    created() {
        this.update();
    },
    methods: {
        async update() {
            this.busy = true;
            const params = { view: "admin_job_list" };
            if (this.showAllRunning) {
                params.state = "running";
            } else {
                const cutoff = Math.floor(this.cutoffMin);
                const dateRangeMin = new Date(Date.now() - cutoff * 60 * 1000).toISOString();
                params.date_range_min = `${dateRangeMin}`;
            }
            const ctx = {
                root: getAppRoot(),
                ...params,
            };
            try {
                const jobs = await jobsProvider(ctx);
                this.jobs = jobs;
                this.loading = false;
                this.busy = false;
                this.status = "info";
            } catch (error) {
                console.log(error);
                this.message = errorMessageAsString(error);
                this.status = "danger";
            }
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
        toggleAll(checked) {
            this.selectedStopJobIds = checked ? this.jobsItemsModel.reduce((acc, j) => [...acc, j["id"]], []) : [];
        },
    },
};
</script>
