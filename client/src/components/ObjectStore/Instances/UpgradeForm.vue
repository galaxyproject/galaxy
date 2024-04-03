<script setup lang="ts">
import { computed, ref } from "vue";

import { errorMessageAsString } from "@/utils/simple-error";

import type { ObjectStoreTemplateSummary } from "../Templates/types";
import { useInstanceRouting } from "./routing";
import { update } from "./services";
import type { UserConcreteObjectStore, VariableData } from "./types";
import { templateSecretFormEntry, templateVariableFormEntry } from "./util";

import InstanceForm from "./InstanceForm.vue";

interface Props {
    instance: UserConcreteObjectStore;
    latestTemplate: ObjectStoreTemplateSummary;
}

const error = ref<string | null>(null);
const props = defineProps<Props>();

const inputs = computed<Array<any> | null>(() => {
    const form = [];
    const realizedInstance: UserConcreteObjectStore = props.instance;
    const realizedLatestTemplate = props.latestTemplate;
    const variables = realizedLatestTemplate.variables ?? [];
    const secrets = realizedLatestTemplate.secrets ?? [];
    const variableValues: VariableData = realizedInstance.variables || {};
    const secretsSet = realizedInstance.secrets || [];
    for (const variable of variables) {
        form.push(templateVariableFormEntry(variable, variableValues[variable.name]));
    }
    for (const secret of secrets) {
        const secretName = secret.name;
        if (secretsSet.indexOf(secretName) >= 0) {
            console.log("skipping...");
        } else {
            form.push(templateSecretFormEntry(secret));
        }
    }
    return form;
});
const title = computed(() => `Upgrade Object Store ${props.instance.name}`);
const submitTitle = "Update Settings";

async function onSubmit(formData: any) {
    const variables = props.latestTemplate.variables ?? [];
    const variableData: VariableData = {};
    for (const variable of variables) {
        variableData[variable.name] = formData[variable.name];
    }
    const secrets = {};
    // ideally we would be able to force a template version here,
    // maybe rework backend types to force this in the API response
    // even if we don't need it in the config files
    const templateVersion: number = props.latestTemplate.version || 0;
    const payload = {
        template_version: templateVersion,
        variables: variableData,
        secrets: secrets,
    };
    const args = { user_object_store_id: String(props.instance.id) };
    try {
        const { data: objectStore } = await update({ ...args, ...payload });
        await onUpgrade(objectStore);
    } catch (e) {
        error.value = errorMessageAsString(e);
        return;
    }
}

const { goToIndex } = useInstanceRouting();

async function onUpgrade(objectStore: UserConcreteObjectStore) {
    const message = `Upgraded object store ${objectStore.name}`;
    goToIndex({ message });
}
</script>
<template>
    <div>
        <b-alert v-if="error" variant="danger" class="object-store-instance-upgrade-error" show>
            {{ error }}
        </b-alert>
        <InstanceForm :inputs="inputs" :title="title" :submit-title="submitTitle" @onSubmit="onSubmit" />
    </div>
</template>
