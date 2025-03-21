<template>
    <div>
        <Alert :message="message" :variant="status" />
        <Alert v-if="viewOnly" message="未实现" variant="dark" />
        <Alert v-else-if="loading" message="等待数据" variant="info" />
        <div v-else-if="dataManagers && !dataManagers.length">
            <Alert variant="primary">
                <span class="alert-heading h-sm">无安装</span>
                您当前没有安装任何数据管理器。
            </Alert>
        </div>
        <div v-else-if="dataManagers && dataTables">
            <b-container fluid>
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
            </b-container>
            <b-card-group columns>
                <b-card id="data-managers-card" no-body header="已安装的数据管理器">
                    <b-list-group flush>
                        <b-list-group-item v-for="(dataManager, index) in dataManagersFiltered" :key="index">
                            <b-button-group vertical>
                                <b-button
                                    :id="kebabCase(dataManager['name'])"
                                    :href="dataManager['toolUrl']"
                                    target="_blank"
                                    variant="primary">
                                    <div>{{ dataManager["name"] }}</div>
                                    <div v-if="dataManager['description']">
                                        <i>{{ dataManager["description"] }}</i>
                                    </div>
                                </b-button>
                                <b-button
                                    :id="kebabCase(dataManager['name']) + '-jobs'"
                                    :to="{
                                        name: 'DataManagerJobs',
                                        params: { id: encodeURIComponent(dataManager['id']) },
                                    }">
                                    作业
                                </b-button>
                            </b-button-group>
                        </b-list-group-item>
                    </b-list-group>
                </b-card>
                <b-card no-body header="工具数据表">
                    <b-list-group flush>
                        <b-list-group-item
                            v-for="(dataTable, index) in dataTablesFiltered"
                            :id="kebabCase(dataTable['name']) + '-table'"
                            :key="index"
                            :to="{ name: 'DataManagerTable', params: { name: dataTable['name'] } }"
                            :variant="dataTable['managed'] === true ? 'primary' : 'link'">
                            {{ dataTable["name"] }}
                            <b-badge v-if="dataTable['managed'] === true" variant="primary" pill
                                ><span class="fa fa-exchange"
                            /></b-badge>
                        </b-list-group-item>
                    </b-list-group>
                </b-card>
            </b-card-group>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { debounce } from "underscore";

import Alert from "components/Alert.vue";

export default {
    components: {
        Alert,
    },
    beforeRouteEnter(to, from, next) {
        console.log("beforeRouteEnter");
        next((vm) => vm.debouncedLoad());
    },
    props: {
        debouncePeriod: { type: Number, required: false, default: 100 },
    },
    data() {
        return {
            dataManagers: [],
            dataTables: [],
            filter: "",
            viewOnly: false,
            message: "",
            status: "",
            loading: false,
        };
    },
    computed: {
        dataManagersFiltered() {
            return this.dataManagers.filter((d) => d["name"].match(new RegExp(this.filter, "i")));
        },
        dataTablesFiltered() {
            return this.dataTables.filter((d) => d["name"].match(new RegExp(this.filter, "i")));
        },
    },
    created() {
        console.log("created");
        this.debouncedLoad = debounce(this.load, this.debouncePeriod);
        this.debouncedLoad();
    },
    methods: {
        kebabCase(s) {
            return s.toLowerCase().replace(/ /g, "-");
        },
        load() {
            this.loading = true;
            axios
                .get(`${getAppRoot()}data_manager/data_managers_list`)
                .then((response) => {
                    console.log("response", response);
                    this.dataManagers = response.data.dataManagers;
                    this.dataTables = response.data.dataTables;
                    this.viewOnly = response.data.viewOnly;
                    this.message = response.data.message;
                    this.status = response.data.status;
                })
                .catch((error) => {
                    console.error(error);
                })
                .finally(() => {
                    this.loading = false;
                });
        },
    },
};
</script>
