<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { submitToolInstallationRequest } from "@/api/notifications";
import { errorMessageAsString } from "@/utils/simple-error";
import { parseRequestedToolParts } from "@/utils/tool-version";

import GModal from "@/components/BaseComponents/GModal.vue";

const props = defineProps<{
    show: boolean;
    missingToolIds: string[];
    /** Encoded StoredWorkflow id, when the workflow lives on this Galaxy. */
    workflowId?: string;
    /** Named in the request instead, for a workflow that isn't on this Galaxy yet. */
    workflowName?: string;
    workflowUrl?: string;
}>();

const emit = defineEmits<{
    (e: "update:show", show: boolean): void;
    (e: "update:submitting", submitting: boolean): void;
    (e: "submitted"): void;
}>();

/** Mirrors the server-side bound on requested-tool entries per request. */
const MAX_REQUESTED_TOOLS = 50;

const submitting = ref(false);
const errorMessage = ref("");

const toolCount = computed(() => props.missingToolIds.length);

function setShow(show: boolean) {
    emit("update:show", show);
    if (!show) {
        // A failed attempt's error belongs to the dialog it was shown in.
        errorMessage.value = "";
    }
}

function setSubmitting(value: boolean) {
    submitting.value = value;
    emit("update:submitting", value);
}

function describeRequest() {
    // The requested tools carry the ids/versions in structured form, so the
    // remarks only add the workflow context (and a note when the request had
    // to be truncated to the server-side limit).
    const toolVerb = toolCount.value === 1 ? "tool is" : "tools are";
    let workflow = "this workflow";
    if (!props.workflowId && props.workflowName) {
        // With no stored workflow the server can't name it, so the admins would otherwise get no context.
        workflow = `the workflow "${props.workflowName}"${props.workflowUrl ? ` (${props.workflowUrl})` : ""}`;
    }
    let description =
        `The requested ${toolVerb} required by ${workflow} but not installed on this instance. ` +
        `These tools are available in the Tool Shed and need to be installed.`;
    if (toolCount.value > MAX_REQUESTED_TOOLS) {
        description += ` Only the first ${MAX_REQUESTED_TOOLS} of ${toolCount.value} missing tools are listed in this request.`;
    }
    return description;
}

async function requestInstallation() {
    setSubmitting(true);
    errorMessage.value = "";

    try {
        await submitToolInstallationRequest({
            tools: props.missingToolIds.slice(0, MAX_REQUESTED_TOOLS).map(parseRequestedToolParts),
            workflow_id: props.workflowId,
            additional_remarks: describeRequest(),
        });

        emit("submitted");
        emit("update:show", false);
    } catch (e) {
        errorMessage.value = errorMessageAsString(e, "Failed to submit installation request. Please try again.");
    } finally {
        setSubmitting(false);
    }
}
</script>

<template>
    <GModal
        :show="props.show"
        title="Request Tool Installation"
        size="small"
        confirm
        ok-text="Send Request"
        :ok-disabled="submitting"
        :cancel-disabled="submitting"
        :close-on-ok="false"
        @ok="requestInstallation"
        @cancel="setShow(false)"
        @update:show="setShow($event)">
        <!-- Inside the dialog: the open <dialog> makes the rest of the page inert,
             so an alert rendered outside it would be hidden behind the backdrop. -->
        <BAlert v-if="errorMessage" variant="danger" show dismissible @dismissed="errorMessage = ''">
            {{ errorMessage }}
        </BAlert>
        <p>
            Request the admins to install
            <strong>{{ toolCount }} missing {{ toolCount === 1 ? "tool" : "tools" }}</strong>
            required by this workflow?
        </p>
        <p class="text-muted small mb-0">
            The admins will receive a notification and can install the tools from the Tool Shed.
        </p>
        <p v-if="toolCount > MAX_REQUESTED_TOOLS" data-testid="truncation-note" class="text-muted small mb-0">
            Only the first {{ MAX_REQUESTED_TOOLS }} of the {{ toolCount }} missing tools will be included in the
            request.
        </p>
    </GModal>
</template>
