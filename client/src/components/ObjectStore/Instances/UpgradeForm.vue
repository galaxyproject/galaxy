<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type FormEntry, upgradeForm, upgradeFormDataToPayload } from "@/components/ConfigTemplates/formUtil";
import { errorMessageAsString } from "@/utils/simple-error";

import type { ObjectStoreTemplateSummary } from "../Templates/types";
import { useInstanceRouting } from "./routing";
import { update } from "./services";
import type { UserConcreteObjectStore } from "./types";

import InstanceForm from "@/components/ConfigTemplates/InstanceForm.vue";

interface Props {
    instance: UserConcreteObjectStore;
    latestTemplate: ObjectStoreTemplateSummary;
}

const error = ref<string | null>(null);
const props = defineProps<Props>();

const inputs = computed<Array<FormEntry> | undefined>(() => {
    const realizedInstance: UserConcreteObjectStore = props.instance;
    const realizedLatestTemplate = props.latestTemplate;
    const form = upgradeForm(realizedLatestTemplate, realizedInstance);
    return form;
});
const title = computed(() => `Upgrade Object Store ${props.instance.name}`);
const submitTitle = "Update Settings";
const loadingMessage = "Loading storage location template and instance information";

async function onSubmit(formData: any) {
    const payload = upgradeFormDataToPayload(props.latestTemplate, formData);
    const args = { user_object_store_id: String(props.instance.uuid) };
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
    const message = `Upgraded storage location ${objectStore.name}`;
    goToIndex({ message });
}
</script>
<template>
    <div>
        <BAlert v-if="error" variant="danger" class="object-store-instance-upgrade-error" show>
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
