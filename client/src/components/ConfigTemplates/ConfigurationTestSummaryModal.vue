<script lang="ts" setup>
import type { PluginStatus } from "@/api/configTemplates";

import GModal from "../BaseComponents/GModal.vue";
import ConfigurationTestSummary from "./ConfigurationTestSummary.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

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
        <GAlert v-if="error" variant="danger" show dismissible>
            {{ error || "" }}
        </GAlert>
        <ConfigurationTestSummary :test-results="testResults" />
    </GModal>
</template>
