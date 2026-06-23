<script lang="ts" setup>
import { BAlert } from "bootstrap-vue";

import type { PluginStatus } from "@/api/configTemplates";

import GModal from "../BaseComponents/GModal.vue";
import ConfigurationTestSummary from "./ConfigurationTestSummary.vue";

interface Props {
    value: boolean;
    testResults?: PluginStatus;
    error?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();
</script>

<template>
    <GModal :show="props.value" title="Configuration Test Summary" size="medium" @close="emit('input', false)">
        <BAlert v-if="error" variant="danger" show dismissible>
            {{ error || "" }}
        </BAlert>
        <ConfigurationTestSummary :test-results="testResults" />
    </GModal>
</template>
