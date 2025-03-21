<template>
    <table class="tabletip">
        <thead>
            <tr>
                <th :colspan="dataManagerColumns.length" style="font-size: 120%">
                    数据管理器: {{ dataManagerTableName }}
                    <a
                        class="icon-btn"
                        href="javascript:void(0)"
                        :title="`重新加载 ${dataManagerTableName} 工具数据表`"
                        @click="handleReloadButtonClick"
                    >
                        <span class="fa fa-sync"></span>
                    </a>
                </th>
            </tr>
            <tr>
                <!-- eslint-disable-next-line vue/require-v-for-key -->
                <th v-for="column in dataManagerColumns">{{ column }}</th>
            </tr>
        </thead>
        <tbody v-for="item in dataManagerItems" :key="item.value">
            <tr>
                <!-- eslint-disable-next-line vue/require-v-for-key -->
                <td v-for="column in dataManagerColumns">{{ item[column] }}</td>
            </tr>
        </tbody>
    </table>
</template>

<script>
export default {
    props: {
        dataManagerTableName: {
            type: String,
            required: true,
        },
        dataManagerColumns: {
            type: Array,
            required: true,
        },
        dataManagerItems: {
            type: Array,
            required: true,
        },
    },
    methods: {
        handleReloadButtonClick(event) {
            this.$emit("reloaddatamanager", this.dataManagerTableName);
        },
    },
};
</script>
