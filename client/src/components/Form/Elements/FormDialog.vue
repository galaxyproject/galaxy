<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import DataDialog from "@/components/DataDialog/DataDialog.vue";
import { onMounted, ref, reactive } from "vue";
import { getCurrentGalaxyHistory } from "@/utils/data";

library.add(faFolderOpen);

interface DataDialogProps {
    id: string;
    multiple?: boolean;
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

const openDataDialog = ref(false);

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
        <button @click="openDataDialog = true">
            <font-awesome-icon icon="folder-open" :title="title" />
        </button>
        <input v-model="dataSelected.value" disabled class="ui-input float-left" />
        <DataDialog
            v-if="openDataDialog"
            :history="localHistoryId.value"
            :multiple="multiple"
            @onCancel="openDataDialog = false"
            @onUpload="openDataDialog = false"
            @onOk="onData" />
    </div>
</template>
