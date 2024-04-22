<script lang="ts" setup>
import { computed, ref } from "vue";

import { create } from "@/components/ObjectStore/Instances/services";
import type { SecretData, UserConcreteObjectStore, VariableData } from "@/components/ObjectStore/Instances/types";
import {
    metadataFormEntryDescription,
    metadataFormEntryName,
    templateSecretFormEntry,
    templateVariableFormEntry,
} from "@/components/ObjectStore/Instances/util";
import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";
import { errorMessageAsString } from "@/utils/simple-error";

import InstanceForm from "./InstanceForm.vue";

interface CreateFormProps {
    template: ObjectStoreTemplateSummary;
}
const error = ref<string | null>(null);
const props = defineProps<CreateFormProps>();
const title = "Create a new storage location for your data";
const submitTitle = "Submit";

const inputs = computed(() => {
    const form = [];
    const variables = props.template.variables ?? [];
    const secrets = props.template.secrets ?? [];
    form.push(metadataFormEntryName());
    form.push(metadataFormEntryDescription());
    for (const variable of variables) {
        form.push(templateVariableFormEntry(variable, undefined));
    }
    for (const secret of secrets) {
        form.push(templateSecretFormEntry(secret));
    }
    return form;
});

async function onSubmit(formData: any) {
    const variables = props.template.variables ?? [];
    const secrets = props.template.secrets ?? [];
    const variableData: VariableData = {};
    const secretData: SecretData = {};
    for (const variable of variables) {
        variableData[variable.name] = formData[variable.name];
    }
    for (const secret of secrets) {
        secretData[secret.name] = formData[secret.name];
    }
    const name: string = formData._meta_name;
    const description: string = formData._meta_description;
    const payload = {
        name: name,
        description: description,
        secrets: secretData,
        variables: variableData,
        template_id: props.template.id,
        template_version: props.template.version ?? 0,
    };
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
    <div>
        <b-alert v-if="error" variant="danger" class="object-store-instance-creation-error" show>
            {{ error }}
        </b-alert>
        <InstanceForm :inputs="inputs" :title="title" :submit-title="submitTitle" @onSubmit="onSubmit" />
    </div>
</template>
