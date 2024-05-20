<script lang="ts" setup>
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { FileSourceTemplateSummary, UserFileSourceModel } from "@/api/fileSources";
import { createFormDataToPayload, createTemplateForm } from "@/components/ConfigTemplates/formUtil";
import { errorMessageAsString } from "@/utils/simple-error";

import { create } from "./services";

import InstanceForm from "@/components/ConfigTemplates/InstanceForm.vue";

interface CreateFormProps {
    template: FileSourceTemplateSummary;
}
const error = ref<string | null>(null);
const props = defineProps<CreateFormProps>();
const title = "Create a new file source for your data";
const submitTitle = "Submit";
const loadingMessage = "Loading file source template and instance information";

const inputs = computed(() => {
    return createTemplateForm(props.template, "file source");
});

async function onSubmit(formData: any) {
    const payload = createFormDataToPayload(props.template, formData);
    try {
        const { data: fileSource } = await create(payload);
        emit("created", fileSource);
    } catch (e) {
        error.value = errorMessageAsString(e);
        return;
    }
}

const emit = defineEmits<{
    (e: "created", fileSource: UserFileSourceModel): void;
}>();
</script>
<template>
    <div id="create-file-source-landing">
        <BAlert v-if="error" variant="danger" class="file-source-instance-creation-error" show>
            {{ error }}
        </BAlert>
        <InstanceForm
            :inputs="inputs"
            :title="title"
            :submit-title="submitTitle"
            :loading-message="loadingMessage"
            @onSubmit="onSubmit" />
    </div>
</template>
