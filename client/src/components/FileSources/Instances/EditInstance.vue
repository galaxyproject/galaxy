<script setup lang="ts">
import { BTab, BTabs } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { UserFileSourceModel } from "@/api/fileSources";
import { editFormDataToPayload, editTemplateForm, type FormEntry } from "@/components/ConfigTemplates/formUtil";

import { useInstanceAndTemplate } from "./instance";
import { useInstanceRouting } from "./routing";
import { update } from "./services";

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

const title = computed(() => `Edit File Source ${instance.value?.name} Settings`);
const hasSecrets = computed(() => instance.value?.secrets && instance.value?.secrets.length > 0);
const submitTitle = "Update Settings";
const loadingMessage = "Loading file source template and instance information";

async function onSubmit(formData: any) {
    if (template.value) {
        const payload = editFormDataToPayload(template.value, formData);
        const args = { user_file_source_id: String(instance?.value?.uuid) };
        const { data: fileSource } = await update({ ...args, ...payload });
        await onUpdate(fileSource);
    }
}

const { goToIndex } = useInstanceRouting();

async function onUpdate(instance: UserFileSourceModel) {
    const message = `Updated file source ${instance.name}`;
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
                    <EditSecrets :file-source="instance" :template="template" />
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
