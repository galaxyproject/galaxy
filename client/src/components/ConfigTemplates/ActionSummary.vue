<script lang="ts" setup>
import { ref } from "vue";

import type { PluginStatus } from "@/api/configTemplates";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
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
        <GAlert v-if="error" variant="danger" class="configuration-instance-error" show>
            <span :data-description="errorDataDescription">
                {{ error }}
            </span>
            <GButton color="blue" transparent @click="showTestResults = true">View configuration test status.</GButton>
        </GAlert>
    </div>
</template>
