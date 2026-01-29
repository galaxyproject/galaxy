<script lang="ts" setup>
import { BAlert, BButton } from "bootstrap-vue";
import { ref } from "vue";

import type { PluginStatus } from "@/api/configTemplates";

import ConfigurationTestSummaryModal from "@/components/ConfigTemplates/ConfigurationTestSummaryModal.vue";

interface Props {
    error: String | null;
    testResults?: PluginStatus;
    errorDataDescription: string;
}

const showTestResults = ref(false);
defineProps<Props>();
</script>

<template>
    <div>
        <ConfigurationTestSummaryModal v-model="showTestResults" :test-results="testResults" />
        <BAlert v-if="error" variant="danger" class="configuration-instance-error" show>
            <span :data-description="errorDataDescription">
                {{ error }}
            </span>
            <BButton variant="link" @click="showTestResults = true">View configuration test status.</BButton>
        </BAlert>
    </div>
</template>
