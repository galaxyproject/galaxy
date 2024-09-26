<script setup lang="ts">
import { computed, toRef } from "vue";

import { type TestUpgradeInstancePayload, type UpgradeInstancePayload } from "@/api/configTemplates";
import { useConfigurationTemplateUpgrade } from "@/components/ConfigTemplates/useConfigurationTesting";

import type { ObjectStoreTemplateSummary } from "../Templates/types";
import { useInstanceRouting } from "./routing";
import { testUpdate, update } from "./services";
import { type UserConcreteObjectStore } from "./types";

interface Props {
    instance: UserConcreteObjectStore;
    latestTemplate: ObjectStoreTemplateSummary;
}

const props = defineProps<Props>();

const title = computed(() => `Upgrade Object Store ${props.instance.name}`);

const {
    error,
    ActionSummary,
    inputs,
    InstanceForm,
    loadingMessage,
    showForceActionButton,
    onForceSubmit,
    onSubmit,
    testRunning,
    testResults,
    submitTitle,
} = useConfigurationTemplateUpgrade(
    "storage location",
    toRef(props, "instance"),
    toRef(props, "latestTemplate"),
    (payload: TestUpgradeInstancePayload) => testUpdate({ user_object_store_id: props.instance.uuid, ...payload }),
    (payload: UpgradeInstancePayload) => update({ user_object_store_id: props.instance.uuid, ...payload }),
    useInstanceRouting
);
</script>
<template>
    <div>
        <ActionSummary error-data-description="object-store-upgrade-error" :test-results="testResults" :error="error" />
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
