<template>
    <base-grid :is-loaded="isLoaded" :columns="columns" id="sanitize-allow-grid">
        <template v-slot:title> Tool Sanitization Allowlist </template>
        <template v-slot:rows>
            <template v-for="(row, index) in rows">
                <tr :key="row.tool_id" :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                    <td>{{ row.tool_name }}</td>
                    <td>{{ row.tool_id }}</td>
                    <td>{{ row.allowed }}</td>
                    <td>{{ row.toolshed }}</td>
                </tr>
            </template>
        </template>
    </base-grid>
</template>

<script>
import BaseGrid from "./BaseGrid.vue";

export default {
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
                { text: "Tool Name", dataIndex: "tool_name" },
                { text: "Tool ID", dataIndex: "tool_id" },
                { text: "Allowed", dataIndex: "allowed" },
                { text: "Tool Type", dataIndex: "tool_type" },
            ],
        };
    },

    components: {
        "base-grid": BaseGrid,
    },

};
</script>
