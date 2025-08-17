<template>
    <div aria-labelledby="data-tables-heading">
        <h1 id="data-tables-heading" class="h-lg">Data Tables</h1>
        <message :message="message" :status="status"></message>
        <component
            v-bind="currentProps"
            :is="currentView"
            v-if="status !== 'error'"
            @changeview="showDataManager"
            @reloaddatamanager="reloadDataManager">
        </component>
    </div>
</template>

<script>
import axios from "axios";

import { GalaxyApi } from "@/api";
import { getAppRoot } from "@/onload/loadConfig";

import Message from "../Message.vue";
import DataManagerGrid from "./DataManagerGrid.vue";
import DataTablesGrid from "./DataTablesGrid.vue";

export default {
    components: {
        message: Message,
        "data-tables-grid": DataTablesGrid,
        "data-manager-grid": DataManagerGrid,
    },
    data() {
        return {
            currentView: "data-tables-grid",
            isLoaded: false,
            dataTables: [],
            dataManagerTableName: "",
            dataManagerColumns: [],
            dataManagerItems: [],
            message: "",
            status: "",
        };
    },

    computed: {
        currentProps() {
            let props;

            if (this.currentView === "data-tables-grid") {
                props = {
                    isLoaded: this.isLoaded,
                    rows: this.dataTables,
                };
            } else {
                props = {
                    dataManagerTableName: this.dataManagerTableName,
                    dataManagerColumns: this.dataManagerColumns,
                    dataManagerItems: this.dataManagerItems,
                };
            }

            return props;
        },
    },

    created() {
        axios
            .get(`${getAppRoot()}admin/data_tables_list`)
            .then((response) => {
                this.isLoaded = true;
                this.dataTables = response.data.data;
                this.message = response.data.message;
                this.status = response.data.status;
            })
            .catch((error) => {
                console.error(error);
            });
    },

    methods: {
        showDataManager(dataManagerTableName) {
            GalaxyApi()
                .GET("/api/tool_data/{table_name}", {
                    params: { path: { table_name: dataManagerTableName } },
                })
                .then(({ data, error }) => {
                    if (error) {
                        this.message = error.err_msg || "Failed to load tool data table.";
                        this.status = "error";
                    } else {
                        this.dataManagerTableName = dataManagerTableName;
                        this.dataManagerColumns = data.columns;
                        this.dataManagerItems = data.fields.map((row) =>
                            Object.fromEntries(data.columns.map((col, i) => [col, row[i]])),
                        );
                        this.currentView = "data-manager-grid";
                    }
                });
        },

        reloadDataManager(dataManagerTableName) {
            GalaxyApi()
                .GET("/api/tool_data/{table_name}/reload", {
                    params: { path: { table_name: dataManagerTableName } },
                })
                .then(({ data, error }) => {
                    if (error) {
                        this.message = error.err_msg || "Failed to reload tool data table.";
                        this.status = "error";
                    } else {
                        this.dataManagerItems = data.fields.map((row) =>
                            Object.fromEntries(data.columns.map((col, i) => [col, row[i]])),
                        );
                        this.message = `Reloaded data table '${dataManagerTableName}'.`;
                        this.status = "done";
                    }
                });
        },
    },
};
</script>
