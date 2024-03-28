<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";

import { type SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

interface HistoryItem {
    id: string;
    name: string;
    created_time: string;
}

interface Props {
    callback?: (results: SelectionItem) => void;
    history: string;
    modalStatic?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    callback: () => {},
    modalStatic: false,
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onOk", results: SelectionItem): void;
    (e: "onUpload"): void;
}>();

const errorMessage = ref("");
const items = ref([]);
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
            items.value = response.data.map((item: HistoryItem) => {
                return {
                    id: item.id,
                    label: item.name,
                    time: item.created_time,
                    isLeaf: true,
                };
            });
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
        :modal-static="modalStatic"
        leaf-icon="fa fa-folder"
        :items="items"
        @onCancel="onCancel"
        @onClick="onClick" />
</template>
