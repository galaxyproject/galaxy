<template>
    <div aria-labelledby="jobs-title">
        <h1 id="jobs-title" class="h-lg">Jobs</h1>
        <b-alert v-if="message" :variant="status" show>
            {{ message }}
        </b-alert>
        <Heading h2 size="md" separator>Job Lock</Heading>
        <JobLock />
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
                    <IndexFilter v-bind="filterAttrs" id="job-search" v-model="filter" />
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
                <b-form-checkbox id="send-notification" v-model="sendNotification" switch class="mb-4">
                    Send a warning notification to users (must provide stop message)
                </b-form-checkbox>
            </b-form>
        </transition>
        <h3 class="mb-0 h-sm">Unfinished Jobs</h3>
        <JobsTable
            v-model="jobsItemsModel"
            :fields="unfinishedJobFields"
            :items="unfinishedJobs"
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
        </JobsTable>

        <template v-if="!showAllRunning">
            <h3 class="mb-0 h-sm">Finished Jobs</h3>
            <JobsTable
                :table-caption="finishedTableCaption"
                :fields="finishedJobFields"
                :items="finishedJobs"
                :no-items-message="finishedNoJobsMessage"
                :loading="loading"
                :busy="busy"
                @tool-clicked="(toolId) => appendTagFilter('tool', toolId)"
                @runner-clicked="(runner) => appendTagFilter('runner', runner)"
                @handler-clicked="(handler) => appendTagFilter('handler', handler)"
                @user-clicked="(user) => appendTagFilter('user', user)">
            </JobsTable>
        </template>
    </div>
</template>

<script>
import axios from "axios";
import JobsTable from "components/admin/JobsTable";
import Heading from "components/Common/Heading";
import filtersMixin from "components/Indices/filtersMixin";
import { jobsProvider } from "components/providers/JobProvider";
import { NON_TERMINAL_STATES } from "components/WorkflowInvocationState/util";
import { getAppRoot } from "onload/loadConfig";
import { errorMessageAsString } from "utils/simple-error";

import { GalaxyApi } from "@/api";

import { commonJobFields } from "./JobFields";
import JobLock from "./JobLock";

function cancelJob(jobId, message) {
    const url = `${getAppRoot()}api/jobs/${jobId}`;
    return axios.delete(url, { data: { message: message } });
}

const helpHtml = `<div>
<p>This textbox box can be used to filter the jobs displayed.

<p>Text entered here will be searched against job user, tool ID, job runner, and handler. Additionally,
advanced filtering tags can be used to refine the search more precisely. Tags are of the form
<code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>.
For instance to search just for jobs with <code>cat1</code> in the tool name, <code>tool:cat1</code> can be used.
Notice by default the search is not case-sensitive.

<p>If the quoted version of tag is used, the search is case sensitive and only full matches will be
returned. So <code>tool:'cat1'</code> would show only jobs from the <code>cat1</code> tool exactly.</p>

<p>The available tags are:
<dl>
    <dt><code>user</code></dt>
    <dd>This filters the job index to contain only jobs executed by matching user(s). You may also just click on a user in the list of jobs to filter on that exact user using this directly.</dd>
    <dt><code>handler</code></dt>
    <dd>This filters the job index to contain only jobs executed on matching handler(s).  You may also just click on a handler in the list of jobs to filter on that exact user using this directly.</dd>
    <dt><code>runner</code></dt>
    <dd>This filters the job index to contain only jobs executed on matching job runner(s).  You may also just click on a runner in the list of jobs to filter on that exact user using this directly.</dd>
    <dt><code>tool</code></dt>
    <dd>This filters the job index to contain only jobs from the matching tool(s).  You may also just click on a tool in the list of jobs to filter on that exact user using this directly.</dd>
</dl>
</div>
`;

export default {
    components: { JobLock, JobsTable, Heading },
    mixins: [filtersMixin],
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
            message: "",
            status: "info",
            loading: true,
            busy: true,
            cutoffMin: 5,
            showAllRunning: false,
            titleSearch: `search jobs`,
            helpHtml: helpHtml,
            sendNotification: false,
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
                if (NON_TERMINAL_STATES.includes(item.state)) {
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
            if (this.filter) {
                params.search = this.filter;
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
        async sendNotificationToUsers(cancelReason) {
            const jobsToCancel = this.unfinishedJobs.filter((job) => this.selectedStopJobIds.includes(job.id));
            const userJobsMap = jobsToCancel.reduce((acc, job) => {
                if (job.user_id) {
                    if (!acc[job.user_id]) {
                        acc[job.user_id] = [];
                    }
                    acc[job.user_id].push(job);
                }
                return acc;
            }, {});
            const userIds = Object.keys(userJobsMap);
            const totalUsers = userIds.length;
            let numSuccess = 0;
            const errors = [];
            for (const userId of userIds) {
                const jobs = userJobsMap[userId];
                // Send a notification per user listing all the jobs IDs that were cancelled
                const notificationRequest = {
                    notification: {
                        source: "admin",
                        variant: "warning",
                        category: "message",
                        content: {
                            category: "message",
                            subject: "Jobs Cancelled by Admin",
                            message: `The following jobs (${jobs
                                .map((job) => `**${job.id}**`)
                                .join(", ")}) were cancelled by an administrator. Reason: **${cancelReason}**.`,
                        },
                    },
                    recipients: {
                        user_ids: [userId],
                    },
                };
                const { error } = await GalaxyApi().POST("/api/notifications", {
                    body: notificationRequest,
                });
                if (error) {
                    errors.push(error);
                } else {
                    numSuccess++;
                }
            }

            if (errors.length) {
                this.message = `Notification sent to ${numSuccess} out of ${totalUsers} users. ${errors.length} errors occurred.`;
                this.status = "warning";
            } else {
                this.message = `Notification sent to ${numSuccess} out of ${totalUsers} users.`;
                this.status = "success";
            }
        },
        onStopJobs() {
            axios.all(this.selectedStopJobIds.map((jobId) => cancelJob(jobId, this.stopMessage))).then((res) => {
                if (this.sendNotification && this.stopMessage) {
                    this.sendNotificationToUsers(this.stopMessage);
                }
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
