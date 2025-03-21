<template>
    <div aria-labelledby="data-types-heading">
        <h1 id="data-types-heading" class="h-lg">数据类型</h1>
        <Message :message="message" :status="status" />
        <BaseGrid
            v-if="status !== 'error'"
            id="data-types-grid"
            :columns="columns"
            :rows="dataTypes"
            :is-loaded="isDataLoaded">
            <template v-slot:title>
                <p>当前数据类型注册包含 {{ dataTypes.length }} 个数据类型。</p>
                <input id="showAllColumns" v-model="showAllColumns" type="checkbox" />
                <label for="showAllColumns">显示所有列</label>
            </template>
        </BaseGrid>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";

import Message from "../Message.vue";
import BaseGrid from "./BaseGrid.vue";

export default {
    components: {
        Message,
        BaseGrid,
    },

    data() {
        return {
            // Show all columns when user wants to
            showAllColumns: false,
            keys: [],
            dataTypes: [],
            message: "",
            status: "",
        };
    },

    computed: {
        // Return predefined column headers merged
        // with all other column headers returned by the api
        columns() {
            let columns = this.prettyColumns();
            // We have keys to look at
            if (this.keys.length > 0) {
                // Additional column headers only when option is selected
                if (this.showAllColumns) {
                    let keys = this.keys;
                    // Filter out the predefined column headers
                    for (const c of columns) {
                        keys = keys.filter((k) => k !== c["dataIndex"]);
                    }
                    // Create column headers from each remaining key and merge
                    // with predefined column headers
                    columns = keys.reduce(function (m, k) {
                        let text = k[0].toUpperCase();
                        text += k.slice(1).replace(/_/g, " ");
                        m.push({
                            text: text,
                            dataIndex: k,
                        });
                        return m;
                    }, columns);
                }
            }
            return columns;
        },
        isDataLoaded() {
            return status !== "" || this.dataTypes.length > 0;
        },
    },

    created() {
        axios
            .get(`${getAppRoot()}admin/data_types_list`)
            .then((response) => {
                this.keys = response.data.keys;
                this.dataTypes = response.data.data;
                this.message = response.data.message;
                this.status = response.data.status;
            })
            .catch((error) => {
                console.error(error);
            });
    },

    methods: {
        // Predefined columns with pretty headers (entries are optional)
        prettyColumns() {
            return [
                { text: "扩展名", dataIndex: "extension" },
                { text: "类型", dataIndex: "type" },
                { text: "MIME 类型", dataIndex: "mimetype" },
                { text: "在上传中显示", dataIndex: "display_in_upload" },
            ];
        },
    },
};
</script>
