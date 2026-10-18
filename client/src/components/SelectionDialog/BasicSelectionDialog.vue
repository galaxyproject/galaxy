<script setup lang="ts">
import { computed, ref } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { basicEntryToItem, type TimedSelectionItem } from "@/components/SelectionDialog/selectionAdapters";
import type { SelectionItem, SelectItemsProvider } from "@/components/SelectionDialog/selectionTypes";
import { useSelectItems } from "@/composables/useSelectItems";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

interface Props {
    detailsKey?: string;
    getData: () => Promise<Array<object> | undefined>;
    isEncoded?: boolean;
    labelKey?: string;
    leafIcon?: string;
    timeKey?: string;
    title: string;
}

const props = withDefaults(defineProps<Props>(), {
    detailsKey: "",
    isEncoded: false,
    labelKey: "id",
    leafIcon: "",
    timeKey: "update_time",
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onOk", results: SelectionItem): void;
    (e: "onUpload"): void;
}>();

const modalShow = ref(true);

// getData() returns every entry, so paging and search run locally
const provider: SelectItemsProvider<Record<string, any>> = {
    load: async () => ({ items: (await props.getData()) ?? [] }),
    map: (entry) => basicEntryToItem(entry, props),
};
const state = useSelectItems(provider);

const showTime = computed(() => state.items.value.some((item) => (item as TimedSelectionItem).time));

const fields = computed<TableField[]>(() => {
    const fields = [{ key: "label", label: "Name" }];
    if (props.detailsKey) {
        fields.push({ key: "details", label: "Details" });
    }
    if (showTime.value) {
        fields.push({ key: "time", label: "Time" });
    }
    return fields;
});
</script>

<template>
    <SelectionDialog
        :fields="fields"
        :modal-show="modalShow"
        :is-encoded="isEncoded"
        :leaf-icon="leafIcon"
        :state="state"
        :title="title"
        @onCancel="emit('onCancel')"
        @onClick="emit('onOk', $event)" />
</template>
