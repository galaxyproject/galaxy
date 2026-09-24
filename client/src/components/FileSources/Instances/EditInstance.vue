<script setup lang="ts">
import { computed, ref } from "vue";

import { useConfigurationTemplateEdit } from "@/components/ConfigTemplates/useConfigurationTesting";

import { useInstanceAndTemplate } from "./instance";
import { useInstanceRouting } from "./routing";

import EditSecrets from "./EditSecrets.vue";
import GTab from "@/components/BaseComponents/GTab.vue";
import GTabs from "@/components/BaseComponents/GTabs.vue";

const editTestUrl = "/api/file_source_instances/{uuid}/test";
const editUrl = "/api/file_source_instances/{uuid}";

interface Props {
    instanceId: string;
}

const props = defineProps<Props>();
const { instance, template } = useInstanceAndTemplate(ref(props.instanceId));

const title = computed(() => `Edit ${template.value?.name} settings for ${instance.value?.name}`);
const errorDataDescription = "file-source-update-error";

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
    submitTitle,
    showForceActionButton,
} = useConfigurationTemplateEdit("file source", instance, template, editTestUrl, editUrl, useInstanceRouting);
</script>
<template>
    <div>
        <GTabs v-if="hasSecrets">
            <GTab title="Settings" active>
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
            </GTab>
            <GTab title="Secrets">
                <div v-if="instance && template">
                    <EditSecrets :file-source="instance" :template="template" />
                </div>
            </GTab>
        </GTabs>
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
