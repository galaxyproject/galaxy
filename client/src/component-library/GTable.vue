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
        <template v-for="(_, slot) of $scopedSlots" v-slot:[slot]="scope">
            <slot :name="slot" v-bind="scope" />
        </template>
    </BTable>
</template>
