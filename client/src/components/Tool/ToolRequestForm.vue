<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { ref } from "vue";

import { submitUserNotification } from "@/api/notifications";
import { errorMessageAsString } from "@/utils/simple-error";

import GModal from "@/components/BaseComponents/GModal.vue";
import FormElement from "@/components/Form/FormElement.vue";

const props = defineProps<{
    show: boolean;
}>();

const emit = defineEmits<{
    (e: "update:show", value: boolean): void;
}>();

const toolName = ref("");
const toolUrl = ref("");
const description = ref("");
const scientificDomain = ref("");
const requestedVersion = ref("");
const additionalRemarks = ref("");

const submitting = ref(false);
const successMessage = ref("");
const errorMessage = ref("");
const urlError = ref("");

const formValid = () => !!(toolName.value.trim() && description.value.trim());

function validateUrl(): boolean {
    const url = toolUrl.value.trim();
    if (!url) {
        urlError.value = "";
        return true;
    }
    try {
        const parsed = new URL(url);
        if (parsed.protocol !== "https:") {
            urlError.value = "Only https:// URLs are allowed.";
            return false;
        }
    } catch {
        urlError.value = "Please enter a valid URL (e.g. https://example.com).";
        return false;
    }
    urlError.value = "";
    return true;
}

function resetForm() {
    toolName.value = "";
    toolUrl.value = "";
    description.value = "";
    scientificDomain.value = "";
    requestedVersion.value = "";
    additionalRemarks.value = "";
    errorMessage.value = "";
    urlError.value = "";
    successMessage.value = "";
}

function close() {
    resetForm();
    emit("update:show", false);
}

async function submit() {
    if (!formValid()) {
        errorMessage.value = "Please fill in all required fields.";
        return;
    }

    if (!validateUrl()) {
        return;
    }

    submitting.value = true;
    errorMessage.value = "";
    successMessage.value = "";

    try {
        await submitUserNotification({
            tool_names: [toolName.value.trim()],
            tool_url: toolUrl.value.trim() || undefined,
            description: description.value.trim(),
            scientific_domain: scientificDomain.value.trim() || undefined,
            requested_version: requestedVersion.value.trim() || undefined,
            additional_remarks: additionalRemarks.value.trim() || undefined,
        });

        submitting.value = false;
        resetForm();
        successMessage.value =
            "Your tool request has been submitted! The instance admins have been notified and will review your request.";
    } catch (e) {
        submitting.value = false;
        errorMessage.value = errorMessageAsString(e, "Failed to submit tool request. Please try again.");
    }
}
</script>

<template>
    <GModal
        :show="props.show"
        title="Request a Tool"
        size="medium"
        confirm
        ok-text="Submit Request"
        :ok-disabled="submitting || !formValid()"
        :close-on-ok="false"
        @ok="submit"
        @cancel="close"
        @update:show="emit('update:show', $event)">
        <BAlert v-if="successMessage" variant="success" show dismissible @dismissed="close">
            {{ successMessage }}
        </BAlert>

        <BAlert v-if="errorMessage" variant="danger" show dismissible @dismissed="errorMessage = ''">
            {{ errorMessage }}
        </BAlert>

        <div v-if="!successMessage">
            <p class="mb-3 text-muted">
                Request a tool to be installed on this Galaxy instance. Your request will be sent to the admins for
                review.
            </p>

            <h6 v-localize class="font-weight-bold mb-2">Tool Information</h6>

            <FormElement
                id="tool-request-name"
                v-model="toolName"
                type="text"
                title="Tool Name"
                help="e.g. FastQC"
                :attributes="{ optional: false }" />

            <FormElement
                id="tool-request-url"
                v-model="toolUrl"
                type="text"
                title="Homepage / Repository URL"
                help="e.g. https://github.com/..."
                :error="urlError || undefined" />

            <FormElement
                id="tool-request-description"
                v-model="description"
                type="text"
                title="Description"
                help="Describe the tool and its scientific use case"
                :attributes="{ area: true, optional: false }" />

            <FormElement
                id="tool-request-domain"
                v-model="scientificDomain"
                type="text"
                title="Scientific Domain"
                help="e.g. Genomics, Proteomics, AI/ML" />

            <FormElement
                id="tool-request-version"
                v-model="requestedVersion"
                type="text"
                title="Requested Version"
                help="e.g. 1.2.0" />

            <FormElement
                id="tool-request-additional-remarks"
                v-model="additionalRemarks"
                type="text"
                title="Additional Remarks"
                help="Any other information that may help the admins"
                :attributes="{ area: true }" />
        </div>
    </GModal>
</template>
