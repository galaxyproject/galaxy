<template>
    <div>
        <b-breadcrumb v-if="dataTable && !loading" id="breadcrumb" :items="breadcrumbItems" />
        <Alert :message="message" :variant="status" />
        <Alert v-if="loading" message="Waiting for data" status="info" />
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
import { GalaxyApi } from "@/api";

import Alert from "@/components/Alert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

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
    async created() {
        const { data, error } = await GalaxyApi().GET("/api/tool_data/{table_name}", {
            params: { path: { table_name: this.name } },
        });
        if (error) {
            this.message = error.err_msg || "Failed to load tool data table.";
            this.status = "error";
        } else {
            this.dataTable = {
                name: data.name,
                columns: data.columns,
                data: data.fields,
            };
        }
        this.loading = false;
    },
    methods: {
        fields(columns) {
            return columns.map((elem, index) => ({ key: index.toString(), label: elem }));
        },
        async reload() {
            const { data, error } = await GalaxyApi().GET("/api/tool_data/{table_name}/reload", {
                params: { path: { table_name: this.dataTableName } },
            });
            if (error) {
                this.message = error.err_msg || "Failed to reload tool data table.";
                this.status = "error";
            } else {
                this.dataTable = {
                    name: data.name,
                    columns: data.columns,
                    data: data.fields,
                };
                this.message = `Reloaded data table '${data.name}'.`;
                this.status = "done";
            }
        },
    },
};
</script>
