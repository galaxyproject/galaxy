<template>
    <div>
        <b-breadcrumb v-if="dataManager && !loading" id="breadcrumb" :items="breadcrumbItems" />
        <Alert :message="message" :variant="status" />
        <Alert v-if="viewOnly" message="未实现" variant="dark" />
        <Alert v-else-if="loading" message="等待数据" variant="info" />
        <Alert v-else-if="jobs && !jobs.length" message="此数据管理器没有任何作业。" variant="primary" />
        <div v-else-if="jobs">
            <b-container fluid class="mb-3">
                <b-row>
                    <b-col md="6">
                        <b-form-group description="搜索字符串或正则表达式">
                            <b-input-group>
                                <b-form-input
                                    v-model="filter"
                                    placeholder="输入进行搜索"
                                    @keyup.esc.native="filter = ''" />
                                <b-input-group-append>
                                    <b-btn :disabled="!filter" @click="filter = ''">清除 (esc)</b-btn>
                                </b-input-group-append>
                            </b-input-group>
                        </b-form-group>
                    </b-col>
                </b-row>
                <b-row>
                    <b-col>
                        <b-button :pressed.sync="showCommandLine" variant="outline-secondary">
                            {{ showCommandLine ? "隐藏" : "显示" }} 命令行
                        </b-button>
                    </b-col>
                </b-row>
            </b-container>
            <b-table
                id="jobs-table"
                :fields="tableFields"
                :items="tableItems"
                :filter="filter"
                hover
                responsive
                striped>
                <template v-slot:cell(actions)="row">
                    <b-button-group>
                        <b-button v-b-tooltip.hover title="Rerun" target="_top" :href="jobs[row.index]['runUrl']">
                            <span class="fa fa-redo" />
                        </b-button>
                        <b-button
                            :id="'job-' + jobs[row.index]['encId']"
                            v-b-tooltip.hover
                            title="查看信息"
                            :to="{ name: 'DataManagerJob', params: { id: jobs[row.index]['encId'] } }">
                            <span class="fa fa-info-circle" />
                        </b-button>
                        <b-button
                            v-if="!showCommandLine"
                            :pressed.sync="row.detailsShowing"
                            @click.stop="row.toggleDetails()">
                            {{ row.detailsShowing ? "隐藏" : "显示" }} 命令行
                        </b-button>
                    </b-button-group>
                </template>
                <template v-slot:row-details="row">
                    <b-card>
                        <h2 class="h-text">命令行</h2>
                        <pre class="code"><code class="command-line">{{ row.item.commandLine }}</code></pre>
                        <template v-slot:footer>
                            <b-button class="mt-3" @click="row.toggleDetails">隐藏信息</b-button>
                        </template>
                    </b-card>
                </template>
            </b-table>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

import Alert from "components/Alert.vue";

export default {
    components: {
        Alert,
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
                { key: "id", label: "作业ID", sortable: true },
                { key: "user" },
                { key: "updateTime", label: "最后更新", sortable: true },
                { key: "state" },
                { key: "actions" },
                { key: "jobRunnerName", label: "作业执行者" },
                { key: "jobRunnerExternalId", label: "PID/集群ID", sortable: true },
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
                    text: "数据管理器",
                    to: { name: "DataManager" },
                },
                {
                    text: this.dataManager["name"] + " ( " + this.dataManager["description"] + " )",
                    href: this.dataManager["toolUrl"],
                    target: "_blank",
                },
                {
                    text: "作业",
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
