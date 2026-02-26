<template>
    <div>
        <BBreadcrumb v-if="dataTable && !loading" id="breadcrumb" :items="breadcrumbItems" />

        <Alert :message="message" :variant="status" />

        <Alert v-if="viewOnly" message="Not implemented" variant="dark" />
        <Alert v-else-if="loading" message="Waiting for data" status="info" />
        <Alert
            v-else-if="dataTable && !dataTable['data'].length"
            message="There are currently no entries in this tool data table."
            variant="primary" />
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
import axios from "axios";
import { BBreadcrumb, BCard, BCol, BContainer, BRow } from "bootstrap-vue";

import { getAppRoot } from "@/onload/loadConfig";

import Alert from "@/components/Alert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GTable from "@/components/Common/GTable.vue";

export default {
    components: {
        Alert,
        BBreadcrumb,
        BCard,
        BCol,
        BContainer,
        BRow,
        FontAwesomeIcon,
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
