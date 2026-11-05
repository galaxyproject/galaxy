<script setup lang="ts">
import axios from "axios";
import { ref } from "vue";

import { type CollectionEntry, collectionToItem } from "@/components/SelectionDialog/selectionAdapters";
import type { SelectionItem, SelectItemsProvider } from "@/components/SelectionDialog/selectionTypes";
import { withPrefix } from "@/utils/redirect";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

interface Props {
    callback?: (results: SelectionItem) => void;
    history: string;
    collectionTypes?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    callback: () => {},
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onOk", results: SelectionItem): void;
    (e: "onUpload"): void;
}>();

const modalShow = ref(true);

const provider: SelectItemsProvider<CollectionEntry> = {
    async load({ signal }) {
        const url = withPrefix(`/api/histories/${props.history}/contents?type=dataset_collection`);
        const { data } = await axios.get<CollectionEntry[]>(url, { signal });
        let collections = data.sort((a, b) => b.hid - a.hid);
        if (props.collectionTypes?.length) {
            collections = collections.filter(
                (item) => item.collection_type && props.collectionTypes!.includes(item.collection_type),
            );
        }
        return { items: collections };
    },
    map: collectionToItem,
};

function onClick(record: SelectionItem) {
    modalShow.value = false;
    props.callback(record);
    emit("onOk", record);
}

/** Called when the modal is hidden */
function onCancel() {
    modalShow.value = false;
    emit("onCancel");
}
</script>

<template>
    <SelectionDialog
        :modal-show="modalShow"
        leaf-icon="fa fa-folder"
        :provider="provider"
        @onCancel="onCancel"
        @onClick="onClick" />
</template>
