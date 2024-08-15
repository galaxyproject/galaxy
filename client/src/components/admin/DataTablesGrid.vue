<template>
    <base-grid id="data-tables-grid" :is-loaded="isLoaded" :columns="columns">
        <template v-slot:title> Current data table registry contains {{ rows.length }} data tables </template>
        <template v-slot:rows>
            <template v-for="row in rows">
                <tr :key="row.id">
                    <td>
                        <a href="javascript:void(0)" @click="handleTableNameClick">{{ row.name }}</a>
                    </td>
                    <td>{{ row.filename }}</td>
                    <td>{{ row.tool_data_path }}</td>
                    <td>{{ row.errors }}</td>
                </tr>
            </template>
        </template>
    </base-grid>
</template>

<script>
import BaseGrid from "./BaseGrid.vue";

export default {
    components: {
        "base-grid": BaseGrid,
    },
    props: {
        isLoaded: {
            type: Boolean,
            required: true,
        },
        rows: {
            type: Array,
            required: true,
        },
    },

    data() {
        return {
            columns: [
                { text: "Name", dataIndex: "name" },
                { text: "Filename", dataIndex: "filename" },
                { text: "Tool data path", dataIndex: "tool_data_path" },
                { text: "Errors", dataIndex: "errors" },
            ],
        };
    },

    methods: {
        handleTableNameClick(event) {
            this.$emit("changeview", event.target.text);
        },
    },
};
</script>
