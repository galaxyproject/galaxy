<template>
    <div>
        <h2 class="mb-3">
            <span id="jobs-title">Jobs</span>
        </h2>
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
                    <b-col>
                        <b-form-group label="Administrative Job Lock" label-for="prevent-job-dispatching">
                            <b-form-checkbox id="prevent-job-dispatching" v-model="jobLock" switch>
                                Job dispatching is currently
                                <strong>{{ jobLockDisplay ? "locked" : "unlocked" }}</strong>
                            </b-form-checkbox>
                        </b-form-group>
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
                        <b-button :pressed.sync="showCommandLine" variant="outline-secondary">
                            {{ showCommandLine ? "Hide" : "Show" }} Command Line
                        </b-button>
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
                <template v-slot:head(selected)="{ rowSelected }">
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
                        :value="data.item['job_info']['id']"
                    ></b-form-checkbox>
                </template>
                <template v-slot:cell(job_info)="data">
                    <b-link :href="data.value['info_url']" target="galaxy_main">
                        {{ data.value["id"] }}
                    </b-link>
                </template>
                <template v-slot:row-details="row">
                    <b-card>
                        <h5>Command Line</h5>
                        <pre
                            class="text-white bg-dark"
                        ><code class="break-word">{{ row.item.command_line }}</code></pre>
                    </b-card>
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
                    <b-link :href="data.value['info_url']" target="galaxy_main">
                        {{ data.value["id"] }}
                    </b-link>
                </template>
                <template v-slot:row-details="row">
                    <b-card>
                        <h5>Command Line</h5>
                        <pre
                            class="text-white bg-dark"
                        ><code class="break-word">{{ row.item.command_line }}</code></pre>
                    </b-card>
                </template>
            </b-table>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";

export default {
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
                { key: "input_dataset", label: "Inputs" },
                { key: "job_runner_name", label: "Job Runner" },
                { key: "job_runner_external_id", label: "PID/Cluster ID", sortable: true }
            ],
            showCommandLine: false,
            cutoff: 180,
            cutoffDisplay: 180,
            jobLock: false,
            jobLockDisplay: false,
            selectedStopJobIds: [],
            allSelected: false,
            indeterminate: false,
            stopMessage: "",
            filter: "",
            message: "",
            status: "",
            loading: true,
            busy: true
        };
    },
    watch: {
        jobLock(newVal) {
            axios
                .get(`${getAppRoot()}admin/jobs_control?job_lock=${this.jobLock}`)
                .then(response => {
                    this.jobLock = response.data.job_lock;
                    this.jobLockDisplay = response.data.job_lock;
                })
                .catch(error => {
                    console.error(error);
                });
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
        }
    },
    methods: {
        update() {
            this.busy = true;
            let params = [];
            params.push(`cutoff=${this.cutoff}`);
            params.push(`stop_msg=${this.stopMessage}`);
            params.push(`stop=${this.selectedStopJobIds.join()}`);
            params = params.join("&");
            axios
                .get(`${getAppRoot()}admin/jobs_list?${params}`)
                .then(response => {
                    this.jobsItems = response.data.jobs;
                    this.recentJobsItems = response.data.recent_jobs;
                    this.cutoffDisplay = response.data.cutoff;
                    this.message = response.data.message;
                    this.status = response.data.status;
                    this.jobLock = response.data.job_lock;
                    this.jobLockDisplay = response.data.job_lock;
                    this.loading = false;
                    this.busy = false;
                })
                .catch(error => {
                    this.message = error.response.data.err_msg;
                    this.status = "error";
                    console.log(error.response);
                });
        },
        onRefresh() {
            this.update();
        },
        onStopJobs() {
            this.update();
            this.selectedStopJobIds = [];
            this.stopMessage = "";
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
                upload: "dark"
            };
            return translateDict[state] || "primary";
        },
        computeItems(items) {
            return items.map(job => {
                return {
                    ...job,
                    _showDetails: false,
                    _cellVariants: { state: this.translateState(job.state) }
                };
            });
        },
        computeFields(fields) {
            const f = Array.from(fields).slice(0);
            if (this.showCommandLine) {
                f.splice(6, 0, {
                    key: "command_line",
                    tdClass: ["text-white", "bg-dark", "break-word"]
                });
            }
            return f;
        },
        toggleAll(checked) {
            this.selectedStopJobIds = checked
                ? this.jobsItemsModel.reduce((acc, j) => [...acc, j["job_info"]["id"]], [])
                : [];
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
                error: "danger"
            };
            if (variant in galaxyKwdToBoostrapDict) {
                return galaxyKwdToBoostrapDict[variant];
            } else {
                return variant;
            }
        }
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
        }
    },
    created() {
        this.update();
    }
};
</script>

<style>
/* Can not be scoped because of command line tdClass */
.break-word {
    white-space: pre-wrap;
    word-break: break-word;
}
</style>
