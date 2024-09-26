<script setup lang="ts">
import { computed, toRef } from "vue";

import { type TestUpgradeInstancePayload, type UpgradeInstancePayload } from "@/api/configTemplates";
import { type FileSourceTemplateSummary, type UserFileSourceModel } from "@/api/fileSources";
import { useConfigurationTemplateUpgrade } from "@/components/ConfigTemplates/useConfigurationTesting";

import { useInstanceRouting } from "./routing";
import { testUpdate, update } from "./services";

interface Props {
    instance: UserFileSourceModel;
    latestTemplate: FileSourceTemplateSummary;
}

const props = defineProps<Props>();

const title = computed(() => `Upgrade File Source ${props.instance.name}`);

const {
    error,
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
} = useConfigurationTemplateUpgrade(
    "file source",
    toRef(props, "instance"),
    toRef(props, "latestTemplate"),
    (payload: TestUpgradeInstancePayload) => testUpdate({ user_file_source_id: props.instance.uuid, ...payload }),
    (payload: UpgradeInstancePayload) => update({ user_file_source_id: props.instance.uuid, ...payload }),
    useInstanceRouting
);
</script>
<template>
    <div>
        <ActionSummary error-data-description="file-source-upgrade-error" :test-results="testResults" :error="error" />
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
</template>
