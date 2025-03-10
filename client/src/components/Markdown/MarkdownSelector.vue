<script setup lang="ts">
import { BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type WorkflowLabel } from "./labels";

import LabelSelector from "./LabelSelector.vue";

interface MarkdownSelectorProps {
    labelTitle?: string;
    labels: WorkflowLabel[];
    argumentName?: string;
}

const props = defineProps<MarkdownSelectorProps>();
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
        <BModal v-model="modalShow" :title="title" ok-title="Continue" @ok="onOk" @cancel="onCancel" @hidden="onCancel">
            <LabelSelector
                v-model="selectedValue"
                class="ml-2"
                :has-labels="hasLabels"
                :label-title="labelTitle ?? ''"
                :labels="labels" />
        </BModal>
    </span>
</template>
