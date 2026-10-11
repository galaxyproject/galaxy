<template>
    <div class="card">
        <div class="card-header">
            <slot name="title">{{ title }}</slot>
        </div>
        <div class="card-body">
            <table class="manage-table" border="0" cellspacing="0" cellpadding="0" width="100%">
                <slot name="columns">
                    <th v-for="column in columns" :key="column.dataIndex">{{ column.text }}</th>
                </slot>
                <slot name="rows">
                    <template v-for="(row, index) in rows" :key="index">
                        <tr>
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
            type: Boolean,
        },
        title: {
            type: String,
            default: "",
        },
        columns: {
            type: Array,
            default: () => [],
        },
        rows: {
            type: Array,
            default: () => [],
        },
    },
};
</script>
<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.card-body {
    overflow: auto;
}

// :deep() because rows and columns may come from the parent's slots, which Vue 3 does not give this scope id
table {
    :deep(td),
    :deep(th) {
        text-align: left;
        padding: 5px;
        line-height: $line-height-base;
    }
    :deep(th) {
        background-color: $table-heading-bg;
    }
    :deep(tr:nth-child(even)) {
        background-color: $table-bg-accent;
    }
}
</style>
