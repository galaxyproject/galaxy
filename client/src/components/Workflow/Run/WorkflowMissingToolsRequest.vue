<script setup lang="ts">
import { computed, ref } from "vue";

import { useCanRequestToolInstallation } from "@/composables/toolInstallationRequest";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import ToolInstallationRequestDialog from "@/components/Workflow/ToolInstallationRequestDialog.vue";

const props = defineProps<{
    missingToolIds: string[];
    /** Encoded StoredWorkflow id; omitted while unknown (e.g. instance-mode run pages still resolving it). */
    workflowId?: string;
}>();

const canRequest = useCanRequestToolInstallation();

const showConfirm = ref(false);
const submitting = ref(false);
const submitted = ref(false);

const showButton = computed(() => canRequest.value && props.missingToolIds.length > 0);

const toolCount = computed(() => props.missingToolIds.length);
</script>

<template>
    <div v-if="showButton" class="workflow-missing-tools-request mt-3">
        <GAlert v-if="submitted" variant="success" show>
            Installation request sent. Check your notifications for updates.
        </GAlert>

        <GButton
            v-else
            data-testid="request-install-btn"
            :disabled="submitting"
            variant="primary"
            size="small"
            @click="showConfirm = true">
            Request Installation ({{ toolCount }} missing {{ toolCount === 1 ? "tool" : "tools" }})
        </GButton>

        <ToolInstallationRequestDialog
            v-model:show="showConfirm"
            :missing-tool-ids="props.missingToolIds"
            :workflow-id="props.workflowId"
            @update:submitting="submitting = $event"
            @submitted="submitted = true" />
    </div>
</template>
