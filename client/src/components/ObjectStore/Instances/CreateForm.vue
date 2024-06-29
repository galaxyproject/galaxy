<script lang="ts" setup>
import { toRef } from "vue";

import { useConfigurationTemplateCreation } from "@/components/ConfigTemplates/useConfigurationTesting";
import type { UserConcreteObjectStore } from "@/components/ObjectStore/Instances/types";
import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

import { create, test } from "./services";

interface CreateFormProps {
    template: ObjectStoreTemplateSummary;
    uuid?: string;
}
const props = defineProps<CreateFormProps>();
const title = "Create a new storage location for your data";

const emit = defineEmits<{
    (e: "created", objectStore: UserConcreteObjectStore): void;
}>();

const { ActionSummary, error, inputs, InstanceForm, onSubmit, submitTitle, loadingMessage, testRunning, testResults } =
    useConfigurationTemplateCreation(
        "storage location",
        toRef(props, "template"),
        toRef(props, "uuid"),
        test,
        create,
        (instance: UserConcreteObjectStore) => emit("created", instance)
    );
</script>
<template>
    <div id="create-object-store-landing">
        <ActionSummary
            error-data-description="object-store-creation-error"
            :test-results="testResults"
            :error="error" />
        <InstanceForm
            :inputs="inputs"
            :title="title"
            :submit-title="submitTitle"
            :loading-message="loadingMessage"
            :busy="testRunning"
            @onSubmit="onSubmit" />
    </div>
</template>
