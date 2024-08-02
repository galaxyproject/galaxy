<script lang="ts" setup>
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import {
    createFormDataToPayload,
    createTemplateForm,
    type FormEntry,
    pluginStatusToErrorMessage,
} from "@/components/ConfigTemplates/formUtil";
import type { UserConcreteObjectStore } from "@/components/ObjectStore/Instances/types";
import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";
import { errorMessageAsString } from "@/utils/simple-error";

import InstanceForm from "@/components/ConfigTemplates/InstanceForm.vue";

interface CreateFormProps {
    template: ObjectStoreTemplateSummary;
}
const error = ref<string | null>(null);
const props = defineProps<CreateFormProps>();
const title = "Create a new storage location for your data";
const submitTitle = "Submit";
const loadingMessage = "Loading storage location template and instance information";

const inputs = computed<Array<FormEntry>>(() => {
    return createTemplateForm(props.template, "storage location");
});

async function onSubmit(formData: any) {
    const payload = createFormDataToPayload(props.template, formData);

    const { data: pluginStatus, error: testRequestError } = await GalaxyApi().POST("/api/object_store_instances/test", {
        body: payload,
    });

    if (testRequestError) {
        error.value = errorMessageAsString(testRequestError);
        return;
    }

    const testError = pluginStatusToErrorMessage(pluginStatus);
    if (testError) {
        error.value = testError;
        return;
    }

    const { data: objectStore, error: createRequestError } = await GalaxyApi().POST("/api/object_store_instances", {
        body: payload,
    });

    if (createRequestError) {
        error.value = errorMessageAsString(createRequestError);
        return;
    }

    emit("created", objectStore);
}

const emit = defineEmits<{
    (e: "created", objectStore: UserConcreteObjectStore): void;
}>();
</script>
<template>
    <div id="create-object-store-landing">
        <BAlert v-if="error" variant="danger" class="object-store-instance-creation-error" show>
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
