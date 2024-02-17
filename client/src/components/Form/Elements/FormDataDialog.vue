<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, watch } from "vue";

import { getCurrentGalaxyHistory } from "@/utils/data";

import DataDialog from "@/components/DataDialog/DataDialog.vue";

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
        <b-input-group>
            <button @click="dataDialogOpen = true">
                <FontAwesomeIcon icon="folder-open" :title="title" />
            </button>
            <input :value="props.value" readonly class="float-left" />
        </b-input-group>
        <DataDialog
            v-if="dataDialogOpen"
            :history="localHistoryId"
            :multiple="multiple"
            @onCancel="dataDialogOpen = false"
            @onUpload="dataDialogOpen = false"
            @onOk="onData" />
    </div>
</template>
