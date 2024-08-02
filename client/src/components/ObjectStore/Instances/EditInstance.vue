<script setup lang="ts">
import { BTab, BTabs } from "bootstrap-vue";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api";
import { editFormDataToPayload, editTemplateForm, type FormEntry } from "@/components/ConfigTemplates/formUtil";
import { rethrowSimple } from "@/utils/simple-error";

import { useInstanceAndTemplate } from "./instance";
import { useInstanceRouting } from "./routing";
import type { UserConcreteObjectStore } from "./types";

import EditSecrets from "./EditSecrets.vue";
import InstanceForm from "@/components/ConfigTemplates/InstanceForm.vue";

interface Props {
    instanceId: string;
}

const props = defineProps<Props>();
const { instance, template } = useInstanceAndTemplate(ref(props.instanceId));

const inputs = computed<Array<FormEntry> | undefined>(() => {
    template.value;
    instance.value;
    if (template.value && instance.value) {
        return editTemplateForm(template.value, "storage location", instance.value);
    }
    return undefined;
});

const title = computed(() => `Edit Storage Location ${instance.value?.name} Settings`);
const hasSecrets = computed(() => instance.value?.secrets && instance.value?.secrets.length > 0);
const submitTitle = "Update Settings";
const loadingMessage = "Loading storage location template and instance information";

async function onSubmit(formData: any) {
    if (template.value) {
        const payload = editFormDataToPayload(template.value, formData);

        const user_object_store_id = instance?.value?.uuid!;

        const { data: objectStore, error } = await GalaxyApi().PUT(
            "/api/object_store_instances/{user_object_store_id}",
            {
                params: { path: { user_object_store_id } },
                body: payload,
            }
        );

        if (error) {
            rethrowSimple(error);
        }

        await onUpdate(objectStore);
    }
}

const { goToIndex } = useInstanceRouting();

async function onUpdate(objectStore: UserConcreteObjectStore) {
    const message = `Updated storage location ${objectStore.name}`;
    goToIndex({ message });
}
</script>
<template>
    <div>
        <BTabs v-if="hasSecrets">
            <BTab title="Settings" active>
                <InstanceForm
                    :inputs="inputs"
                    :title="title"
                    :submit-title="submitTitle"
                    :loading-message="loadingMessage"
                    @onSubmit="onSubmit" />
            </BTab>
            <BTab title="Secrets">
                <div v-if="instance && template">
                    <EditSecrets :object-store="instance" :template="template" />
                </div>
            </BTab>
        </BTabs>
        <InstanceForm
            v-else
            :inputs="inputs"
            :title="title"
            :submit-title="submitTitle"
            :loading-message="loadingMessage"
            @onSubmit="onSubmit" />
    </div>
</template>
