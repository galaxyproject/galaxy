<script setup lang="ts">
import { computed } from "vue";

import type { UserFileSourceModel } from "@/api/fileSources";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";

import { useInstanceRouting } from "./routing";

import CreateForm from "@/components/FileSources/Instances/CreateForm.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    templateId: string;
}
const fileSourceTemplatesStore = useFileSourceTemplatesStore();
fileSourceTemplatesStore.fetchTemplates();

const { goToIndex } = useInstanceRouting();

const props = defineProps<Props>();
const template = computed(() => fileSourceTemplatesStore.getLatestTemplate(props.templateId));

async function onCreated(objectStore: UserFileSourceModel) {
    const message = `Created file source ${objectStore.name}`;
    goToIndex({ message });
}
</script>

<template>
    <div>
        <LoadingSpan v-if="!template" message="Loading file source templates" />
        <CreateForm v-else :template="template" @created="onCreated"></CreateForm>
    </div>
</template>
