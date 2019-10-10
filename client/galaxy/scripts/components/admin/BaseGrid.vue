<template>
    <div class="card">
        <div class="card-header">
            <slot name="title">{{ title }}</slot>
        </div>
        <div class="card-body">
            <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                <slot name="columns">
                    <th v-for="column in columns" bgcolor="#D8D8D8" :key="column.dataIndex">{{ column.text }}</th>
                </slot>
                <slot name="rows">
                    <template v-for="(row, index) in rows">
                        <!-- eslint-disable-next-line vue/require-v-for-key -->
                        <tr :class="[index % 2 === 0 ? 'tr' : 'odd_row']">
                            <td v-for="column in columns" :key="column.dataIndex">{{ row[column.dataIndex] }}</td>
                        </tr>
                    </template>
                </slot>
            </table>
            <div v-if="isLoaded !== undefined && !isLoaded" :style="{ textAlign: 'center', padding: '7px 0' }">
                Loading...
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        isLoaded: {
            type: Boolean
        },
        title: {
            type: String
        },
        columns: {
            type: Array
        },
        rows: {
            type: Array
        }
    }
};
</script>
<style>
.card-body {
    overflow: auto;
}
</style>
