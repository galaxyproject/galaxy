<script lang="ts" setup>
import { BTable } from "bootstrap-vue";
import { computed, ref } from "vue";

interface Props {
    value?: [];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: Props["value"]): void;
}>();

const tableRef = ref();

const model = computed({
    get: () => props.value,
    set: (value) => {
        emit("input", value);
    },
});

function clearSelected() {
    tableRef.value.clearSelected();
}

const items = computed(() => {
    return tableRef.value.items;
});

function refresh() {
    tableRef.value.refresh();
}

defineExpose({
    clearSelected,
    items,
    refresh,
});
</script>

<template>
    <BTable ref="tableRef" v-model="model" v-bind="$attrs" v-on="$listeners">
        <template v-slot:empty>
            <slot name="empty"></slot>
        </template>

        <template v-slot:head()="data">
            <slot :name="`head(${data.field.key})`" v-bind="data"></slot>
        </template>

        <template v-slot:cell()="data">
            <slot :name="`cell(${data.field.key})`" v-bind="data"></slot>
        </template>

        <template v-slot:row-details="row">
            <slot name="row-details" v-bind="row"></slot>
        </template>

        <template v-slot:table-caption>
            <slot name="table-caption"></slot>
        </template>

        <slot></slot>
    </BTable>
</template>
