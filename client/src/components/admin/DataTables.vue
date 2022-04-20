<template>
    <div>
        <message :message="message" :status="status"></message>
        <component
            :is="currentView"
            v-if="status !== 'error'"
            v-bind="currentProps"
            @changeview="showDataManager"
            @reloaddatamanager="reloadDataManager">
        </component>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import Message from "../Message.vue";
import DataTablesGrid from "./DataTablesGrid.vue";
import DataManagerGrid from "./DataManagerGrid.vue";

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
            axios
                .get(`${getAppRoot()}data_manager/tool_data_table_items`, {
                    params: {
                        table_name: dataManagerTableName,
                    },
                })
                .then((response) => {
                    this.message = response.data.message;
                    this.status = response.data.status;

                    if (response.data.status !== "error" && response.data.status !== "warning") {
                        this.dataManagerTableName = dataManagerTableName;
                        this.dataManagerColumns = response.data.data.columns;
                        this.dataManagerItems = response.data.data.items;
                        this.currentView = "data-manager-grid";
                    }
                })
                .catch((error) => {
                    console.error(error);
                });
        },

        reloadDataManager(dataManagerTableName) {
            axios
                .get(`${getAppRoot()}data_manager/reload_tool_data_table`, {
                    params: {
                        table_name: dataManagerTableName,
                    },
                })
                .then((response) => {
                    this.message = response.data.message;
                    this.status = response.data.status;

                    if (response.data.status !== "error" && response.data.status !== "warning") {
                        this.dataManagerItems = response.data.data.items;
                    }
                })
                .catch((error) => {
                    console.error(error);
                });
        },
    },
};
</script>
