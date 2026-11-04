<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";

import { type CollectionEntry, collectionToItem } from "@/components/SelectionDialog/selectionAdapters";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

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

const errorMessage = ref("");
const items = ref<SelectionItem[]>([]);
const modalShow = ref(true);
const optionsShow = ref(false);

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

/** Performs server request to retrieve data records **/
function load() {
    optionsShow.value = false;
    const url = withPrefix(`/api/histories/${props.history}/contents?type=dataset_collection`);
    axios
        .get(url)
        .then((response) => {
            let collection_instances = response.data.sort((a: CollectionEntry, b: CollectionEntry) => b.hid - a.hid);
            if (props.collectionTypes?.length) {
                collection_instances = collection_instances.filter(
                    (item: CollectionEntry) =>
                        item.collection_type && props.collectionTypes!.includes(item.collection_type),
                );
            }
            items.value = collection_instances.map(collectionToItem);
            optionsShow.value = true;
        })
        .catch((error) => {
            errorMessage.value = errorMessageAsString(error);
        });
}

onMounted(() => {
    load();
});
</script>

<template>
    <SelectionDialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        leaf-icon="fa fa-folder"
        :items="items"
        @onCancel="onCancel"
        @onClick="onClick" />
</template>
