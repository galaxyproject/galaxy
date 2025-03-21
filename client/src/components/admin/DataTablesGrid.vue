<template>
    <base-grid id="data-tables-grid" :is-loaded="isLoaded" :columns="columns">
        <template v-slot:title> 当前数据表注册包含 {{ rows.length }} 个数据表 </template>
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
                { text: "名称", dataIndex: "name" },
                { text: "文件名", dataIndex: "filename" },
                { text: "工具数据路径", dataIndex: "tool_data_path" },
                { text: "错误", dataIndex: "errors" },
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
