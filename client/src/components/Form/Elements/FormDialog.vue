<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import DataDialog from "@/components/DataDialog/DataDialog.vue";
import { ref, watch } from "vue";
import { getCurrentGalaxyHistory } from "@/utils/data";

library.add(faFolderOpen);

interface DataDialogProps {
    id: string;
    multiple?: boolean;
    value?: Array<string> | string;
}

const props = withDefaults(defineProps<DataDialogProps>(), {
    multiple: false,
    value: "",
});

const title = "Browse Datasets";
const localHistoryId = ref("");
const dataDialogOpen = ref(false);

watch(
    () => dataDialogOpen.value,
    async () => {
        localHistoryId.value = "";
        localHistoryId.value = await getCurrentGalaxyHistory();
    }
);

const emit = defineEmits<{
    (e: "input", value: Array<string> | string): void;
}>();

function onData(result: Array<string> | string) {
    dataDialogOpen.value = false;
    emit("input", result);
}
</script>

<template>
    <div class="d-flex">
        <button @click="dataDialogOpen = true">
            <font-awesome-icon icon="folder-open" :title="title" />
        </button>
        <input :value="props.value" disabled class="ui-input float-left" />
        <DataDialog
            v-if="dataDialogOpen"
            :history="localHistoryId"
            :multiple="multiple"
            @onCancel="dataDialogOpen = false"
            @onUpload="dataDialogOpen = false"
            @onOk="onData" />
    </div>
</template>
