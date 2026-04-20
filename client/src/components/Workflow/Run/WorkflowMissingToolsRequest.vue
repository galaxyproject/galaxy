<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { submitToolRequest } from "@/api/toolRequestForm";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const props = defineProps<{
    missingToolIds: string[];
    workflowName?: string;
}>();

const { config, isConfigLoaded } = useConfig();
const userStore = useUserStore();

const showConfirm = ref(false);
const submitting = ref(false);
const submitted = ref(false);
const errorMessage = ref("");

const storageKey = computed(() => {
    const sorted = [...props.missingToolIds].sort().join(",");
    return `galaxy-tool-install-request:${sorted}`;
});

const alreadyRequested = computed(() => {
    try {
        return !!localStorage.getItem(storageKey.value);
    } catch {
        return false;
    }
});

const showButton = computed(
    () =>
        isConfigLoaded.value &&
        config.value?.enable_tool_request_form &&
        !userStore.isAnonymous &&
        props.missingToolIds.length > 0,
);

const toolCount = computed(() => props.missingToolIds.length);

async function requestInstallation() {
    submitting.value = true;
    errorMessage.value = "";

    const toolListText = props.missingToolIds.join(", ");
    const workflowLabel = props.workflowName ? `workflow "${props.workflowName}"` : "a workflow";
    const toolVerb = toolCount.value === 1 ? "tool is" : "tools are";
    const description =
        `The following ${toolVerb} required by ${workflowLabel} but not installed on this instance: ` +
        `${toolListText}. These tools are available in the Tool Shed and need to be installed.`;

    try {
        await submitToolRequest({
            tool_name:
                toolCount.value === 1
                    ? props.missingToolIds[0]!
                    : `${toolCount.value} tools required by ${workflowLabel}`,
            description,
            tool_ids: props.missingToolIds,
            workflow_name: props.workflowName,
        });

        try {
            localStorage.setItem(storageKey.value, String(Date.now()));
        } catch {
            // localStorage unavailable, silently ignore
        }

        submitted.value = true;
        showConfirm.value = false;
    } catch (e) {
        errorMessage.value = errorMessageAsString(e, "Failed to submit installation request. Please try again.");
    } finally {
        submitting.value = false;
    }
}
</script>

<template>
    <div v-if="showButton" class="workflow-missing-tools-request mt-3">
        <BAlert v-if="errorMessage" variant="danger" show dismissible @dismissed="errorMessage = ''">
            {{ errorMessage }}
        </BAlert>

        <BAlert v-if="submitted || alreadyRequested" variant="success" show>
            Installation request sent — admins have been notified and will review it shortly.
        </BAlert>

        <GButton
            v-else
            data-testid="request-install-btn"
            :disabled="submitting"
            variant="primary"
            size="small"
            @click="showConfirm = true">
            Request Installation ({{ toolCount }} missing {{ toolCount === 1 ? "tool" : "tools" }})
        </GButton>

        <GModal
            :show="showConfirm"
            title="Request Tool Installation"
            size="small"
            confirm
            ok-text="Send Request"
            :ok-disabled="submitting"
            :close-on-ok="false"
            @ok="requestInstallation"
            @cancel="showConfirm = false"
            @update:show="showConfirm = $event">
            <p>
                Request the admins to install
                <strong>{{ toolCount }} missing {{ toolCount === 1 ? "tool" : "tools" }}</strong>
                <span v-if="workflowName">
                    required by workflow <em>{{ workflowName }}</em></span
                >?
            </p>
            <p class="text-muted small mb-0">
                The admins will receive a notification and can install the tools from the Tool Shed.
            </p>
        </GModal>
    </div>
</template>
