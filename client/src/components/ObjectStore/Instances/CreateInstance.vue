<script setup lang="ts">
import { computed } from "vue";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import { useInstanceRouting } from "./routing";
import type { UserConcreteObjectStore } from "./types";

import CreateForm from "./CreateForm.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    templateId: string;
}
const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
objectStoreTemplatesStore.fetchTemplates();

const { goToIndex } = useInstanceRouting();

const props = defineProps<Props>();
const template = computed(() => objectStoreTemplatesStore.getLatestTemplate(props.templateId));

async function onCreated(objectStore: UserConcreteObjectStore) {
    const message = `Created storage location ${objectStore.name}`;
    goToIndex({ message });
}
</script>

<template>
    <div>
        <LoadingSpan v-if="!template" message="Loading storage location templates" />
        <CreateForm v-else :template="template" @created="onCreated"></CreateForm>
    </div>
</template>
