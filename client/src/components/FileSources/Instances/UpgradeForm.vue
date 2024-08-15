<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";

import type { FileSourceTemplateSummary, UserFileSourceModel } from "@/api/fileSources";
import { type FormEntry, upgradeForm, upgradeFormDataToPayload } from "@/components/ConfigTemplates/formUtil";
import { errorMessageAsString } from "@/utils/simple-error";

import { useInstanceRouting } from "./routing";
import { update } from "./services";

import InstanceForm from "@/components/ConfigTemplates/InstanceForm.vue";

interface Props {
    instance: UserFileSourceModel;
    latestTemplate: FileSourceTemplateSummary;
}

const error = ref<string | null>(null);
const props = defineProps<Props>();

const inputs = computed<Array<FormEntry> | undefined>(() => {
    const realizedInstance: UserFileSourceModel = props.instance;
    const realizedLatestTemplate = props.latestTemplate;
    const form = upgradeForm(realizedLatestTemplate, realizedInstance);
    return form;
});
const title = computed(() => `Upgrade File Source ${props.instance.name}`);
const submitTitle = "Update Settings";
const loadingMessage = "Loading file source template and instance information";

async function onSubmit(formData: any) {
    const payload = upgradeFormDataToPayload(props.latestTemplate, formData);
    const args = { user_file_source_id: String(props.instance.uuid) };
    try {
        const { data: fileSource } = await update({ ...args, ...payload });
        await onUpgrade(fileSource);
    } catch (e) {
        error.value = errorMessageAsString(e);
        return;
    }
}

const { goToIndex } = useInstanceRouting();

async function onUpgrade(fileSource: UserFileSourceModel) {
    const message = `Upgraded file source ${fileSource.name}`;
    goToIndex({ message });
}
</script>
<template>
    <div>
        <BAlert v-if="error" variant="danger" class="file-source-instance-upgrade-error" show>
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
