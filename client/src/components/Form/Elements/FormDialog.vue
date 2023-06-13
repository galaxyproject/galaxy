<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import DataDialog from "../../DataDialog/DataDialog.vue";
import { onMounted } from "vue";
import { getCurrentGalaxyHistory } from "../../../utils/data";
import { reactive } from "vue";

library.add(faFolderOpen);

interface DataDialogProps {
    id: string;
    multiple: boolean;
    value?: Array<string> | string;
}

const props = withDefaults(defineProps<DataDialogProps>(), {
    multiple: false,
});

const title = "Browse Datasets";
const historyID: string = "";
const localHistoryId = reactive({
    value: historyID,
});

onMounted(() => {
    getCurrentGalaxyHistory().then((historyId) => {
        localHistoryId.value = historyId;
    });
});

const initialODD = false;
const openDataDialog = reactive({
    value: initialODD,
});

const dataSelected = reactive({
    value: props.value,
});

const emit = defineEmits<{
    (e: "input", value: Array<string> | string): void;
}>();

function onData(result: Array<string> | string) {
    openDataDialog.value = false;
    dataSelected.value = result;
    emit("input", result);
}
</script>

<template>
    <div class="d-flex">
        <span @click="openDataDialog.value = true">
            <font-awesome-icon icon="folder-open" :title="title" />
            <input v-model="dataSelected.value" disabled class="ui-input float-left" />
        </span>
        <DataDialog
            v-if="openDataDialog.value"
            :history="localHistoryId.value"
            :multiple="multiple"
            @onCancel="openDataDialog.value = false"
            @onUpload="openDataDialog.value = false"
            @onOk="onData" />
    </div>
</template>
