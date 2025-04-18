<script setup lang="ts">
import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import { storeToRefs } from "pinia";
import { ref } from "vue";

import { fetchDatasetDetails } from "@/api/datasets";
import { useResourceWatcher } from "@/composables/resourceWatcher";
import { useHistoryStore } from "@/stores/historyStore";
import { uploadPayload } from "@/utils/upload-payload.js";
import { uploadSubmit } from "@/utils/upload-submit.js";
import { stateIsTerminal } from "@/utils/utils";

import ButtonSpinner from "@/components/Common/ButtonSpinner.vue";

const { currentHistoryId } = storeToRefs(useHistoryStore());

const props = defineProps<{
    icon: IconDefinition;
    title: string;
    payload: Record<string, string>;
}>();

const emit = defineEmits<{
    (e: "ok", outputs: any): void;
}>();

const buttonTitle = ref(props.title);
const buttonVariant = ref("outline-primary");
const buttonWait = ref(false);
const outputs = ref();

let stopWatching: any = null;

function handleError(errorMessage: string) {
    buttonTitle.value = errorMessage;
    buttonVariant.value = "outline-danger";
    buttonWait.value = false;
}

function onSubmit() {
    buttonTitle.value = props.title;
    buttonWait.value = true;
    try {
        const payload = uploadPayload([{ fileMode: "new", fileUri: props.payload.url }], currentHistoryId.value);
        uploadSubmit({
            data: payload,
            success: (result: any) => {
                outputs.value = result.outputs.map((output: any) => output.id);
                const { startWatchingResource, stopWatchingResource } = useResourceWatcher(watchJob);
                startWatchingResource();
                stopWatching = stopWatchingResource;
            },
        });
    } catch (err) {
        handleError(String(err));
    }
}

async function watchJob() {
    try {
        const dataset = await fetchDatasetDetails({ id: outputs.value[0] }, "summary");
        if (stateIsTerminal(dataset)) {
            stopWatching();
            buttonWait.value = false;
            emit("ok", dataset);
        }
    } catch (err) {
        handleError(String(err));
    }
}
</script>

<template>
    <ButtonSpinner
        size="sm"
        :icon="icon"
        :title="buttonTitle"
        :variant="buttonVariant"
        :wait="buttonWait"
        @onClick="onSubmit()" />
</template>
