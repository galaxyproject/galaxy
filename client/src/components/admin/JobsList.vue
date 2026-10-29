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
            Unfinished jobs (in the 'new', 'queued', 'running', or 'waiting' states) and finished jobs (in 'error' or
            'ok' states) are displayed below.
        </p>
        <p>
            You may choose to stop some of the unfinished jobs and provide the user with a message. Your stop message
            will be displayed to the user as:
        </p>
        <p>
            "This job was stopped by an administrator:
            <strong>&lt;YOUR MESSAGE&gt;</strong>
            For more information or help, report this error".
        </p>
        <b-row>
            <b-col class="col-sm-4">
                <b-form-group>
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
                <b-form-group>
                    <FilterMenu
                        id="job-search"
                        name="jobs"
                        placeholder="search jobs"
                        :filter-class="filterClass"
                        :filter-text.sync="filter"
                        has-help
                        :loading="busy"
                        :show-advanced.sync="showAdvanced">
                        <template v-slot:menu-help-text>
                            <div>
                                <p>This textbox box can be used to filter the jobs displayed.</p>

                                <p>
                                    Text entered here will be searched against job user, tool ID, job runner, and
                                    handler. Additionally, advanced filtering tags can be used to refine the search more
                                    precisely. Tags are of the form
                                    <code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or
                                    <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>. For instance to search just for
                                    jobs with <code>cat1</code> in the tool name, <code>tool:cat1</code> can be used.
                                    Notice by default the search is not case-sensitive.
                                </p>

                                <p>
                                    If the quoted version of tag is used, the search is case sensitive and only full
                                    matches will be returned. So <code>tool:'cat1'</code> would show only jobs from the
                                    <code>cat1</code> tool exactly.
                                </p>

                                <p>The available tags are:</p>
                                <dl>
                                    <dt><code>user</code></dt>
                                    <dd>
                                        This filters the job index to contain only jobs executed by matching user(s).
                                        You may also just click on a user in the list of jobs to filter on that exact
                                        user using this directly.
                                    </dd>
                                    <dt><code>handler</code></dt>
                                    <dd>
                                        This filters the job index to contain only jobs executed on matching handler(s).
                                        You may also just click on a handler in the list of jobs to filter on that exact
                                        user using this directly.
                                    </dd>
                                    <dt><code>runner</code></dt>
                                    <dd>
                                        This filters the job index to contain only jobs executed on matching job
                                        runner(s). You may also just click on a runner in the list of jobs to filter on
                                        that exact user using this directly.
                                    </dd>
                                    <dt><code>tool</code></dt>
                                    <dd>
                                        This filters the job index to contain only jobs from the matching tool(s). You
                                        may also just click on a tool in the list of jobs to filter on that exact user
                                        using this directly.
                                    </dd>
                                </dl>
                            </div>
                        </template>
                    </FilterMenu>
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
                            <b-btn type="submit" :disabled="stopping">Submit</b-btn>
                        </b-input-group-append>
                    </b-input-group>
                </b-form-group>
                <b-form-group
                    description="Only one notification will be sent for each user containing the reason and the list of affected jobs.">
                    <b-form-checkbox id="send-notification" v-model="sendNotification" switch>
                        Send a warning notification to users
                    </b-form-checkbox>
                </b-form-group>
            </b-form>
        </transition>
        <h3 class="mb-0 h-sm">Unfinished Jobs</h3>
        <JobsTable
            :fields="unfinishedJobFields"
            :items="unfinishedJobs"
            :table-caption="runningTableCaption"
            :no-items-message="runningNoJobsMessage"
            :loading="loading"
            :busy="busy"
            @tool-clicked="(toolId) => appendTagFilter('tool', toolId)"
            @runner-clicked="(runner) => appendTagFilter('runner', runner)"
            @handler-clicked="(handler) => appendTagFilter('handler', handler)"
            @user-clicked="(user) => appendTagFilter('user', user)">
            <template v-slot:head(selected)>
                <b-form-checkbox
                    v-model="allSelected"
                    :indeterminate="indeterminate"
                    :disabled="stopping"
                    @change="toggleAll"></b-form-checkbox>
            </template>
            <template v-slot:cell(selected)="data">
                <b-form-checkbox
                    :key="data.index"
                    v-model="selectedStopJobIds"
                    :checked="allSelected"
                    :disabled="stopping"
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
import { ref } from "vue";

import { GalaxyApi } from "@/api";
import { NON_TERMINAL_STATES, stopJobs } from "@/api/jobs";
import { jobsProvider } from "@/components/providers/JobProvider";
import { getAppRoot } from "@/onload/loadConfig";
import Filtering, { contains } from "@/utils/filtering";
import { errorMessageAsString } from "@/utils/simple-error";

import { commonJobFields } from "./JobFields";

import JobLock from "./JobLock.vue";
import JobsTable from "@/components/admin/JobsTable.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";

export default {
    components: { FilterMenu, JobLock, JobsTable, Heading },
    setup() {
        const filter = ref("");
        const showAdvanced = ref(false);

        const filterClass = new Filtering(
            {
                user: { placeholder: "user email", type: String, handler: contains("user"), menuItem: true },
                handler: { placeholder: "handler", type: String, handler: contains("handler"), menuItem: true },
                runner: { placeholder: "job runner", type: String, handler: contains("runner"), menuItem: true },
                tool: { placeholder: "tool id", type: String, handler: contains("tool"), menuItem: true },
            },
            undefined,
            false,
        );

        function appendTagFilter(filterName, filterVal) {
            filter.value = filterClass.setFilterValue(filter.value, filterName, `'${filterVal}'`);
        }

        return {
            appendTagFilter,
            filter,
            filterClass,
            showAdvanced,
        };
    },
    data() {
        return {
            jobs: [],
            finishedJobs: [],
            unfinishedJobs: [],
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
            sendNotification: false,
            stopping: false,
        };
    },
    computed: {
        finishedTableCaption() {
            return `These jobs have completed in the previous ${this.cutoffMin} minutes.`;
        },
        runningTableCaption() {
            let message = `These jobs are unfinished`;
            if (!this.showAllRunning) {
                message += ` and have had their state updated in the previous ${this.cutoffMin} minutes`;
            }
            message += `. For currently running jobs, the "Last Update" column should indicate the runtime so far.`;
            return message;
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
            } else if (newVal.length === this.unfinishedJobs.length) {
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
            const unfinishedIds = unfinishedJobs.map((job) => job.id);
            this.selectedStopJobIds = this.selectedStopJobIds.filter((id) => unfinishedIds.includes(id));
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
                params.state = NON_TERMINAL_STATES;
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
                return true;
            } catch (error) {
                console.log(error);
                this.message = errorMessageAsString(error);
                this.status = "danger";
                return false;
            }
        },
        onRefresh() {
            this.update();
        },
        async sendNotificationToUsers(jobIds) {
            const cancelReason = this.stopMessage || "No reason provided";
            const ids = new Set(jobIds);
            const jobsToCancel = this.unfinishedJobs.filter((job) => ids.has(job.id));
            // Group jobs by user
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
                const notificationMessage = `The following jobs (${jobs
                    .map((job) => `**[${job.tool_id || job.id}](${this.getJobViewLink(job.id)})**`)
                    .join(", ")}) were cancelled by an administrator. Reason: **${cancelReason}**.`;

                const { error } = await GalaxyApi().POST("/api/notifications", {
                    body: {
                        notification: {
                            source: "admin",
                            variant: "warning",
                            category: "message",
                            content: {
                                category: "message",
                                subject: "Jobs Cancelled by Admin",
                                message: notificationMessage,
                            },
                        },
                        recipients: {
                            user_ids: [userId],
                        },
                    },
                });
                if (error) {
                    errors.push(error);
                } else {
                    numSuccess++;
                }
            }

            if (errors.length) {
                return {
                    ok: false,
                    message: `Notification sent to ${numSuccess} out of ${totalUsers} users. ${errors.length} errors occurred.`,
                };
            }
            return { ok: true, message: `Notification sent to ${numSuccess} out of ${totalUsers} users.` };
        },
        getJobViewLink(jobId) {
            return `${getAppRoot()}jobs/${jobId}/view`;
        },
        async onStopJobs() {
            const jobIds = [...this.selectedStopJobIds];
            const total = jobIds.length;
            const jobsNoun = total === 1 ? "job" : "jobs";
            this.stopping = true;
            this.status = "info";
            this.message = `Stopping ${total} ${jobsNoun}...`;
            const { stopped, failed } = await stopJobs(jobIds, this.stopMessage, (done) => {
                this.message = `Stopping jobs (${done}/${total})...`;
            });
            let message = `Stopped ${stopped.length} of ${total} ${jobsNoun}.`;
            if (failed.length) {
                message += ` ${failed.length} could not be stopped and remain selected: ${failed[0].error.message}`;
            }
            let notificationFailed = false;
            if (this.sendNotification && stopped.length) {
                try {
                    const notification = await this.sendNotificationToUsers(stopped);
                    message += ` ${notification.message}`;
                    notificationFailed = !notification.ok;
                } catch (error) {
                    message += ` Notifications could not be sent: ${errorMessageAsString(error)}`;
                    notificationFailed = true;
                }
            }
            // Keep failed jobs selected (and the stop message) so the admin can resubmit.
            this.selectedStopJobIds = failed.map(({ jobId }) => jobId);
            if (!failed.length) {
                this.stopMessage = "";
            }
            this.stopping = false;
            if (await this.update()) {
                this.message = message;
                this.status = failed.length ? "danger" : notificationFailed ? "warning" : "success";
            } else {
                // Keep the refresh error visible next to the stop summary.
                this.message = `${message} Refreshing the job list failed: ${this.message}`;
            }
        },
        toggleAll(checked) {
            this.selectedStopJobIds = checked ? this.unfinishedJobs.map((job) => job.id) : [];
        },
    },
};
</script>
