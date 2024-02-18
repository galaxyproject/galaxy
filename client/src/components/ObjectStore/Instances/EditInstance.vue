<script setup lang="ts">
import { computed, ref } from "vue";

import {
    metadataFormEntryDescription,
    metadataFormEntryName,
    templateVariableFormEntry,
} from "@/components/ObjectStore/Instances/util";

import { useInstanceAndTemplate } from "./instance";
import { useInstanceRouting } from "./routing";
import { update } from "./services";
import type { UserConcreteObjectStore, VariableData } from "./types";

import EditSecrets from "./EditSecrets.vue";
import InstanceForm from "./InstanceForm.vue";

interface Props {
    instanceId: number | string;
}

const props = defineProps<Props>();
const { instance, template } = useInstanceAndTemplate(ref(props.instanceId));

const inputs = computed(() => {
    if (!template.value || !instance.value) {
        return null;
    }
    const form = [];
    const nameInput = metadataFormEntryName();
    form.push({ value: instance?.value?.name ?? "", ...nameInput });

    const descriptionInput = metadataFormEntryDescription();
    form.push({ value: instance?.value?.description ?? "", ...descriptionInput });

    if (template.value && instance.value) {
        const realizedInstance: UserConcreteObjectStore = instance.value;
        const variables = template.value?.variables ?? [];
        const variableValues: VariableData = realizedInstance.variables || {};
        for (const variable of variables) {
            form.push(templateVariableFormEntry(variable, variableValues[variable.name]));
        }
    }
    return form;
});

const title = computed(() => `Edit Object Store ${instance.value?.name} Settings`);
const hasSecrets = computed(() => instance.value?.secrets && instance.value?.secrets.length > 0);
const submitTitle = "Update Settings";

async function onSubmit(formData: any) {
    const variables = template?.value?.variables ?? [];
    const name = formData["_meta_name"];
    const description = formData["_meta_description"];
    const variableData: VariableData = {};
    for (const variable of variables) {
        variableData[variable.name] = formData[variable.name];
    }
    const payload = {
        name: name,
        description: description,
        variables: variableData,
    };
    const args = { user_object_store_id: String(instance?.value?.id) };
    const { data: objectStore } = await update({ ...args, ...payload });
    await onUpdate(objectStore);
}

const { goToIndex } = useInstanceRouting();

async function onUpdate(objectStore: UserConcreteObjectStore) {
    const message = `Updated object store ${objectStore.name}`;
    goToIndex({ message });
}
</script>
<template>
    <div>
        <b-tabs v-if="hasSecrets">
            <b-tab title="Settings" active>
                <InstanceForm :inputs="inputs" :title="title" :submit-title="submitTitle" @onSubmit="onSubmit" />
            </b-tab>
            <b-tab title="Secrets">
                <div v-if="instance && template">
                    <EditSecrets :object-store="instance" :template="template" />
                </div>
            </b-tab>
        </b-tabs>
        <InstanceForm v-else :inputs="inputs" :title="title" :submit-title="submitTitle" @onSubmit="onSubmit" />
    </div>
</template>
