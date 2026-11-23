<script lang="ts" setup>
import type { PluginStatus } from "@/api/configTemplates";

import GModal from "../BaseComponents/GModal.vue";
import ConfigurationTestSummary from "./ConfigurationTestSummary.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

interface Props {
    modelValue: boolean;
    testResults?: PluginStatus;
    error?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:modelValue", value: boolean): void;
}>();
</script>

<template>
    <GModal
        :show="props.modelValue"
        title="Configuration Test Summary"
        size="medium"
        @close="emit('update:modelValue', false)">
        <GAlert v-if="error" variant="danger" show dismissible>
            {{ error || "" }}
        </GAlert>
        <ConfigurationTestSummary :test-results="testResults" />
    </GModal>
</template>
