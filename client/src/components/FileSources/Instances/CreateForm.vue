<script lang="ts" setup>
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import type { FileSourceTemplateSummary, UserFileSourceModel } from "@/api/fileSources";
import {
    createFormDataToPayload,
    createTemplateForm,
    pluginStatusToErrorMessage,
} from "@/components/ConfigTemplates/formUtil";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

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
    const { data: pluginStatus, error: testRequestError } = await GalaxyApi().POST("/api/file_source_instances/test", {
        body: payload,
    });

    if (testRequestError) {
        rethrowSimple(testRequestError);
    }

    const testError = pluginStatusToErrorMessage(pluginStatus);
    if (testError) {
        error.value = testError;
        return;
    }

    const { data: fileSource, error: requestError } = await GalaxyApi().POST("/api/file_source_instances", {
        body: payload,
    });

    if (requestError) {
        error.value = errorMessageAsString(requestError);
        return;
    }

    emit("created", fileSource);
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
