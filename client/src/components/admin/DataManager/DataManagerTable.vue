<template>
    <div>
        <b-breadcrumb v-if="dataTable && !loading" id="breadcrumb" :items="breadcrumbItems" />
        <Alert :message="message" :variant="status" />
        <Alert v-if="viewOnly" message="未实现" variant="dark" />
        <Alert v-else-if="loading" message="等待数据" status="info" />
        <Alert
            v-else-if="dataTable && !dataTable['data'].length"
            message="当前工具数据表中没有任何条目."
            variant="primary" />
        <b-container v-else-if="dataTable">
            <b-row>
                <b-col>
                    <b-card id="data-table-card" flush>
                        <template v-slot:header>
                            <b-container>
                                <b-row align-v="center">
                                    <b-col cols="auto">
                                        <b-button v-b-tooltip.hover :title="buttonLabel" @click="reload()">
                                            <span class="fa fa-sync" />
                                        </b-button>
                                    </b-col>
                                    <b-col>
                                        <b>{{ dataTableName }}</b>
                                    </b-col>
                                </b-row>
                            </b-container>
                        </template>
                        <b-table
                            :fields="fields(dataTable['columns'])"
                            :items="dataTable['data']"
                            small
                            hover
                            striped />
                    </b-card>
                </b-col>
            </b-row>
        </b-container>
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
        name: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            dataTable: {},
            viewOnly: false,
            message: "",
            status: "",
            loading: true,
        };
    },
    computed: {
        dataTableName() {
            return this.dataTable && this.dataTable.name ? this.dataTable.name : "空";
        },
        buttonLabel() {
            return `重新加载 ${this.dataTableName} 工具数据表`;
        },
        breadcrumbItems() {
            return [
                {
                    text: "工具数据表",
                    to: "/admin/data_manager",
                },
                {
                    text: this.dataTableName,
                },
            ];
        },
    },
    created() {
        axios
            .get(`${getAppRoot()}data_manager/tool_data_table_info?table_name=${this.name}`)
            .then((response) => {
                this.dataTable = response.data.dataTable;
                this.viewOnly = response.data.viewOnly;
                this.message = response.data.message;
                this.status = response.data.status;
                this.loading = false;
            })
            .catch((error) => {
                console.error(error);
            });
    },
    methods: {
        fields(columns) {
            return columns.map((elem, index) => ({ key: index.toString(), label: elem }));
        },
        reload() {
            axios
                .get(`${getAppRoot()}data_manager/reload_tool_data_tables?table_name=${this.dataTableName}`)
                .then((response) => {
                    if (response.data.dataTable) {
                        this.dataTable = response.data.dataTable;
                    }
                    this.message = response.data.message;
                    this.status = response.data.status;
                })
                .catch((error) => {
                    console.error(error);
                });
        },
    },
};
</script>
