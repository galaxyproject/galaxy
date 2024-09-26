<script setup lang="ts">
import { BTab, BTabs } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type TestUpdateInstancePayload, type UpdateInstancePayload } from "@/api/configTemplates";
import { useConfigurationTemplateEdit } from "@/components/ConfigTemplates/useConfigurationTesting";

import { useInstanceAndTemplate } from "./instance";
import { useInstanceRouting } from "./routing";
import { testUpdate, update } from "./services";

import EditSecrets from "./EditSecrets.vue";

interface Props {
    instanceId: string;
}

const props = defineProps<Props>();
const { instance, template } = useInstanceAndTemplate(ref(props.instanceId));

const title = computed(() => `Edit Storage Location ${instance.value?.name} Settings`);
const errorDataDescription = "object-store-update-error";

const {
    error,
    hasSecrets,
    ActionSummary,
    inputs,
    InstanceForm,
    loadingMessage,
    onForceSubmit,
    onSubmit,
    testRunning,
    testResults,
    showForceActionButton,
    submitTitle,
} = useConfigurationTemplateEdit(
    "storage location",
    instance,
    template,
    (payload: TestUpdateInstancePayload) => testUpdate({ user_object_store_id: props.instanceId, ...payload }),
    (payload: UpdateInstancePayload) => update({ user_object_store_id: props.instanceId, ...payload }),
    useInstanceRouting
);
</script>
<template>
    <div>
        <BTabs v-if="hasSecrets">
            <BTab title="Settings" active>
                <ActionSummary
                    :error-data-description="errorDataDescription"
                    :test-results="testResults"
                    :error="error" />
                <InstanceForm
                    :inputs="inputs"
                    :title="title"
                    :submit-title="submitTitle"
                    :loading-message="loadingMessage"
                    :busy="testRunning"
                    :show-force-action-button="showForceActionButton"
                    @onForceSubmit="onForceSubmit"
                    @onSubmit="onSubmit" />
            </BTab>
            <BTab title="Secrets">
                <div v-if="instance && template">
                    <EditSecrets :object-store="instance" :template="template" />
                </div>
            </BTab>
        </BTabs>
        <div v-else>
            <ActionSummary :error-data-description="errorDataDescription" :test-results="testResults" :error="error" />
            <InstanceForm
                :inputs="inputs"
                :title="title"
                :submit-title="submitTitle"
                :loading-message="loadingMessage"
                :busy="testRunning"
                :show-force-action-button="showForceActionButton"
                @onForceSubmit="onForceSubmit"
                @onSubmit="onSubmit" />
        </div>
    </div>
</template>
