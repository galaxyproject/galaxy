<template>
    <div aria-labelledby="jobs-title">
        <h1 id="jobs-title" class="h-lg">作业</h1>
        <b-alert v-if="message" :variant="status" show>
            {{ message }}
        </b-alert>
        <Heading h2 size="md" separator>作业锁定</Heading>
        <JobLock />
        <Heading h2 size="md" separator>作业概览</Heading>
        <p>
            以下是未完成的作业（处于“新建”，“排队”，“运行”或“上传”状态）以及最近完成的作业（处于“错误”或“正常”状态）。
        </p>
        <p>
            您可以选择停止显示的某些作业，并向用户提供消息。您的停止消息将显示给用户： “此作业已由管理员停止：
            <strong>&lt;您的消息&gt;</strong>
            如需更多信息或帮助，请报告此错误”。
        </p>
        <b-row>
            <b-col class="col-sm-4">
                <b-form-group description="选择是否使用下面的截止时间。">
                    <b-form-checkbox id="show-all-running" v-model="showAllRunning" switch size="lg" @change="update">
                        {{ showAllRunning ? "显示所有未完成的作业" : "查询应用了时间截止" }}
                    </b-form-checkbox>
                </b-form-group>
                <b-form name="jobs" @submit.prevent="onRefresh">
                    <b-form-group
                        v-show="!showAllRunning"
                        id="cutoff"
                        label="分钟为单位的截止时间"
                        description="显示在给定时间段内状态已更新的作业。">
                        <b-input-group>
                            <b-form-input id="cutoff" v-model="cutoffMin" type="number"> </b-form-input>
                        </b-input-group>
                    </b-form-group>
                </b-form>
                <b-form-group description="使用字符串或正则表达式来搜索作业。">
                    <IndexFilter v-bind="filterAttrs" id="job-search" v-model="filter" />
                </b-form-group>
            </b-col>
        </b-row>
        <transition name="fade">
            <b-form v-if="unfinishedJobs.length && selectedStopJobIds.length" @submit.prevent="onStopJobs">
                <b-form-group label="停止选中的作业" description="停止消息将显示给用户">
                    <b-input-group>
                        <b-form-input id="stop-message" v-model="stopMessage" placeholder="停止消息" required>
                        </b-form-input>
                        <b-input-group-append>
                            <b-btn type="submit">提交</b-btn>
                        </b-input-group-append>
                    </b-input-group>
                </b-form-group>
            </b-form>
        </transition>
        <h3 class="mb-0 h-sm">未完成的作业</h3>
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
            <h3 class="mb-0 h-sm">已完成的作业</h3>
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

import { commonJobFields } from "./JobFields";
import JobLock from "./JobLock";

function cancelJob(jobId, message) {
    const url = `${getAppRoot()}api/jobs/${jobId}`;
    return axios.delete(url, { data: { message: message } });
}

const helpHtml = `<div>
<p>此文本框可用于过滤显示的作业。</p>

<p>在此输入的文本将搜索作业用户、工具 ID、作业执行器和处理程序。此外，您还可以使用高级过滤标签来更精确地细化搜索。标签格式为
<code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> 或 <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>。
例如，要搜索工具名称中包含 <code>cat1</code> 的作业，可以使用 <code>tool:cat1</code>。
默认情况下，搜索不区分大小写。</p>

<p>如果使用了标签的引用版本，搜索将区分大小写，并且仅返回完全匹配的结果。所以 <code>tool:'cat1'</code> 将仅显示来自
<code>cat1</code> 工具的作业。</p>

<p>可用的标签包括：
<dl>
    <dt><code>user</code></dt>
    <dd>此标签用于过滤作业索引，仅显示由匹配的用户执行的作业。您还可以直接点击作业列表中的用户来过滤该用户的作业。</dd>
    <dt><code>handler</code></dt>
    <dd>此标签用于过滤作业索引，仅显示由匹配的处理程序执行的作业。您还可以直接点击作业列表中的处理程序来过滤该处理程序的作业。</dd>
    <dt><code>runner</code></dt>
    <dd>此标签用于过滤作业索引，仅显示由匹配的作业执行器执行的作业。您还可以直接点击作业列表中的执行器来过滤该执行器的作业。</dd>
    <dt><code>tool</code></dt>
    <dd>此标签用于过滤作业索引，仅显示来自匹配工具的作业。您还可以直接点击作业列表中的工具来过滤该工具的作业。</dd>
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
            finishedJobFields: [...commonJobFields, { key: "update_time", label: "已完成", sortable: true }],
            unfinishedJobFields: [
                { key: "selected", label: "" },
                ...commonJobFields,
                { key: "update_time", label: "最后更新", sortable: true },
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
            titleSearch: `搜索作业`,
            helpHtml: helpHtml,
        };
    },
    computed: {
        finishedTableCaption() {
            return `这些作业已在过去 ${this.cutoffMin} 分钟内完成。`;
        },
        runningTableCaption() {
            return `这些作业未完成，并且在过去 ${this.cutoffMin} 分钟内更新了状态。对于当前运行的作业，“最后更新”列应显示目前的运行时间。`;
        },
        finishedNoJobsMessage() {
            return `当前截止时间 ${this.cutoffMin} 分钟内没有已完成的作业。`;
        },
        runningNoJobsMessage() {
            let message = `没有未完成的作业` ;
            if (!this.showAllRunning) {
                message += `，当前截止时间为 ${this.cutoffMin} 分钟`;
            }
            message += "。";
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
