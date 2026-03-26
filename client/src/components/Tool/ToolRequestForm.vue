<script setup lang="ts">
import { BAlert, BFormGroup, BFormInput, BFormSelect, BFormTextarea } from "bootstrap-vue";
import { ref } from "vue";

import { submitToolRequest } from "@/api/toolRequestForm";
import { errorMessageAsString } from "@/utils/simple-error";

import GModal from "@/components/BaseComponents/GModal.vue";

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
const condaAvailable = ref<boolean | null>(null);
const testDataAvailable = ref<boolean | null>(null);
const requesterName = ref("");
const requesterEmail = ref("");
const requesterAffiliation = ref("");

const submitting = ref(false);
const successMessage = ref("");
const errorMessage = ref("");

const formValid = () => !!(toolName.value.trim() && description.value.trim() && requesterName.value.trim());

function resetForm() {
    toolName.value = "";
    toolUrl.value = "";
    description.value = "";
    scientificDomain.value = "";
    requestedVersion.value = "";
    condaAvailable.value = null;
    testDataAvailable.value = null;
    requesterName.value = "";
    requesterEmail.value = "";
    requesterAffiliation.value = "";
    errorMessage.value = "";
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

    submitting.value = true;
    errorMessage.value = "";
    successMessage.value = "";

    try {
        await submitToolRequest({
            tool_name: toolName.value.trim(),
            tool_url: toolUrl.value.trim() || undefined,
            description: description.value.trim(),
            scientific_domain: scientificDomain.value.trim() || undefined,
            requested_version: requestedVersion.value.trim() || undefined,
            conda_available: condaAvailable.value ?? undefined,
            test_data_available: testDataAvailable.value ?? undefined,
            requester_name: requesterName.value.trim(),
            requester_email: requesterEmail.value.trim() || undefined,
            requester_affiliation: requesterAffiliation.value.trim() || undefined,
        });

        submitting.value = false;
        successMessage.value =
            "Your tool request has been submitted! The instance admins have been notified and will review your request.";
        // Reset form fields but keep the success message visible
        toolName.value = "";
        toolUrl.value = "";
        description.value = "";
        scientificDomain.value = "";
        requestedVersion.value = "";
        condaAvailable.value = null;
        testDataAvailable.value = null;
        requesterName.value = "";
        requesterEmail.value = "";
        requesterAffiliation.value = "";
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

            <BFormGroup label="Tool Name *" label-for="tool-request-name">
                <BFormInput
                    id="tool-request-name"
                    v-model="toolName"
                    placeholder="e.g. FastQC"
                    :disabled="submitting"
                    required />
            </BFormGroup>

            <BFormGroup label="Homepage / Repository URL" label-for="tool-request-url">
                <BFormInput
                    id="tool-request-url"
                    v-model="toolUrl"
                    placeholder="e.g. https://github.com/..."
                    :disabled="submitting" />
            </BFormGroup>

            <BFormGroup label="Description *" label-for="tool-request-description">
                <BFormTextarea
                    id="tool-request-description"
                    v-model="description"
                    placeholder="Describe the tool and its scientific use case"
                    rows="3"
                    :disabled="submitting"
                    required />
            </BFormGroup>

            <BFormGroup label="Scientific Domain" label-for="tool-request-domain">
                <BFormInput
                    id="tool-request-domain"
                    v-model="scientificDomain"
                    placeholder="e.g. Genomics, Proteomics, AI/ML"
                    :disabled="submitting" />
            </BFormGroup>

            <BFormGroup label="Requested Version" label-for="tool-request-version">
                <BFormInput
                    id="tool-request-version"
                    v-model="requestedVersion"
                    placeholder="e.g. 1.2.0"
                    :disabled="submitting" />
            </BFormGroup>

            <div class="d-flex gap-3 mb-3">
                <BFormGroup label="Conda package available?" label-for="tool-request-conda" class="flex-fill mb-0">
                    <BFormSelect
                        id="tool-request-conda"
                        v-model="condaAvailable"
                        :options="[
                            { value: null, text: 'Not specified' },
                            { value: true, text: 'Yes' },
                            { value: false, text: 'No' },
                        ]"
                        :disabled="submitting" />
                </BFormGroup>

                <BFormGroup label="Test data available?" label-for="tool-request-test-data" class="flex-fill mb-0">
                    <BFormSelect
                        id="tool-request-test-data"
                        v-model="testDataAvailable"
                        :options="[
                            { value: null, text: 'Not specified' },
                            { value: true, text: 'Yes' },
                            { value: false, text: 'No' },
                        ]"
                        :disabled="submitting" />
                </BFormGroup>
            </div>

            <h6 v-localize class="font-weight-bold mb-2 mt-3">Requester Information</h6>

            <BFormGroup label="Name *" label-for="tool-request-requester-name">
                <BFormInput
                    id="tool-request-requester-name"
                    v-model="requesterName"
                    placeholder="Your name"
                    :disabled="submitting"
                    required />
            </BFormGroup>

            <BFormGroup label="Email (for follow-up)" label-for="tool-request-requester-email">
                <BFormInput
                    id="tool-request-requester-email"
                    v-model="requesterEmail"
                    type="email"
                    placeholder="your@email.com"
                    :disabled="submitting" />
            </BFormGroup>

            <BFormGroup label="Affiliation / Lab" label-for="tool-request-requester-affiliation">
                <BFormInput
                    id="tool-request-requester-affiliation"
                    v-model="requesterAffiliation"
                    placeholder="Your institution or lab"
                    :disabled="submitting" />
            </BFormGroup>
        </div>
    </GModal>
</template>
