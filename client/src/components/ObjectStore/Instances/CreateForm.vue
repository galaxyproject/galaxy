<script lang="ts" setup>
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { createFormDataToPayload, createTemplateForm, type FormEntry } from "@/components/ConfigTemplates/formUtil";
import type { UserConcreteObjectStore } from "@/components/ObjectStore/Instances/types";
import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";
import { errorMessageAsString } from "@/utils/simple-error";

import { create } from "./services";

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
    try {
        const { data: objectStore } = await create(payload);
        emit("created", objectStore);
    } catch (e) {
        error.value = errorMessageAsString(e);
        return;
    }
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
