<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BInputGroup } from "bootstrap-vue";
import { ref, watch } from "vue";

import { getCurrentGalaxyHistory } from "@/utils/data";

import DataDialog from "@/components/DataDialog/DataDialog.vue";

library.add(faFolderOpen);

type Value = string | string[];

interface Props {
    id: string;
    multiple?: boolean;
    value?: Value;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: Value): void;
}>();

const localHistoryId = ref("");
const dataDialogOpen = ref(false);

function onData(result: string[] | string) {
    dataDialogOpen.value = false;

    emit("input", result);
}

watch(
    () => dataDialogOpen.value,
    async () => {
        localHistoryId.value = "";
        localHistoryId.value = await getCurrentGalaxyHistory();
    }
);
</script>

<template>
    <div class="d-flex">
        <BInputGroup>
            <button @click="dataDialogOpen = true">
                <FontAwesomeIcon :icon="faFolderOpen" title="Browse Datasets" />
            </button>

            <input :value="props.value" readonly class="float-left" />
        </BInputGroup>

        <DataDialog
            v-if="dataDialogOpen"
            :history="localHistoryId"
            :multiple="multiple"
            @onCancel="dataDialogOpen = false"
            @onUpload="dataDialogOpen = false"
            @onOk="onData" />
    </div>
</template>
