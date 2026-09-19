<script setup lang="ts">
import { computed, ref } from "vue";

import type { WorkflowLabel } from "./Editor/types";

import GModal from "../BaseComponents/GModal.vue";
import LabelSelector from "./LabelSelector.vue";

const props = defineProps<{
    argumentName: string;
    labelTitle?: string;
    labels: Array<WorkflowLabel>;
}>();

const selectedValue = ref<WorkflowLabel | undefined>(undefined);
const modalShow = ref(true);

const title = computed(() => {
    return `Insert '${props.argumentName}'`;
});
const hasLabels = computed(() => {
    return props.labels && props.labels.length > 0;
});

const emit = defineEmits<{
    (e: "onOk", value: WorkflowLabel | undefined): void;
    (e: "onCancel"): void;
}>();

function onOk() {
    emit("onOk", selectedValue.value);
}

function onCancel() {
    emit("onCancel");
}
</script>

<template>
    <span>
        <GModal :show.sync="modalShow" :title="title" confirm ok-text="Continue" @ok="onOk" @close="onCancel">
            <LabelSelector
                v-model="selectedValue"
                class="ml-2"
                :has-labels="hasLabels"
                :label-title="labelTitle ?? ''"
                :labels="labels" />
        </GModal>
    </span>
</template>
