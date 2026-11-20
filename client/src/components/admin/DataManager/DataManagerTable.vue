<template>
    <div>
        <BBreadcrumb v-if="dataTable && !loading" id="breadcrumb" :items="breadcrumbItems" />

        <GAlert v-if="message" :variant="statusVariant">{{ message }}</GAlert>
        <GAlert v-if="loading" variant="info">Waiting for data</GAlert>
        <GAlert v-else-if="dataTable && !dataTable['data'].length" variant="primary">
            There are currently no entries in this tool data table.
        </GAlert>
        <BContainer v-else-if="dataTable">
            <BRow>
                <BCol>
                    <BCard id="data-table-card" flush>
                        <template v-slot:header>
                            <BContainer>
                                <BRow align-v="center">
                                    <BCol cols="auto">
                                        <GButton tooltip :title="buttonLabel" @click="reload()">
                                            <FontAwesomeIcon :icon="faSync" />
                                        </GButton>
                                    </BCol>

                                    <BCol>
                                        <b>{{ dataTableName }}</b>
                                    </BCol>
                                </BRow>
                            </BContainer>
                        </template>

                        <GTable
                            compact
                            hover
                            striped
                            :fields="fields(dataTable['columns'])"
                            :items="dataTable['data']" />
                    </BCard>
                </BCol>
            </BRow>
        </BContainer>
    </div>
</template>

<script>
import { faSync } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBreadcrumb, BCard, BCol, BContainer, BRow } from "bootstrap-vue";

import { GalaxyApi } from "@/api";
import { alertVariant } from "@/utils/alertVariant";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GTable from "@/components/Common/GTable.vue";

export default {
    components: {
        BBreadcrumb,
        BCard,
        BCol,
        BContainer,
        BRow,
        FontAwesomeIcon,
        GAlert,
        GButton,
        GTable,
    },
    props: {
        name: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            faSync,
            dataTable: {},
            message: "",
            status: "",
            loading: true,
        };
    },
    computed: {
        statusVariant() {
            return alertVariant(this.status);
        },
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
