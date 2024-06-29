<script lang="ts" setup>
import { BAlert, BModal } from "bootstrap-vue";
import { ref, watch } from "vue";

import type { PluginStatus } from "@/api/configTemplates";

import ConfigurationTestSummary from "./ConfigurationTestSummary.vue";

interface Props {
    value: boolean;
    testResults?: PluginStatus;
    error?: string;
}

const props = defineProps<Props>();

const show = ref(props.value);

watch(props, () => {
    show.value = props.value;
});

const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();

watch(show, () => {
    emit("input", show.value);
});
</script>

<template>
    <BModal v-model="show" title="Configuration Test Summary" hide-footer>
        <BAlert v-if="error" variant="danger" show dismissible>
            {{ error || "" }}
        </BAlert>
        <ConfigurationTestSummary :test-results="testResults" />
    </BModal>
</template>
