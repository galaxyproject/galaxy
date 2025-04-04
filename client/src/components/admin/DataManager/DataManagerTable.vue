<template>
    <div>
        <b-breadcrumb v-if="dataTable && !loading" id="breadcrumb" :items="breadcrumbItems" />
        <Alert :message="message" :variant="status" />
        <Alert v-if="viewOnly" message="Not implemented" variant="dark" />
        <Alert v-else-if="loading" message="Waiting for data" status="info" />
        <Alert
            v-else-if="dataTable && !dataTable['data'].length"
            message="There are currently no entries in this tool data table."
            variant="primary" />
        <b-container v-else-if="dataTable">
            <b-row>
                <b-col>
                    <b-card id="data-table-card" flush>
                        <template v-slot:header>
                            <b-container>
                                <b-row align-v="center">
                                    <b-col cols="auto">
                                        <GButton tooltip :title="buttonLabel" @click="reload()">
                                            <span class="fa fa-sync" />
                                        </GButton>
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

import GButton from "@/components/BaseComponents/GButton.vue";
import Alert from "components/Alert.vue";

export default {
    components: {
        Alert,
        GButton,
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
            return this.dataTable && this.dataTable.name ? this.dataTable.name : "null";
        },
        buttonLabel() {
            return `Reload ${this.dataTableName} tool data table`;
        },
        breadcrumbItems() {
            return [
                {
                    text: "Tool Data Tables",
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
