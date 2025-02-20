<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import localize from "@/utils/localization";

import { useInstanceRouting } from "./routing";
import type { UserConcreteObjectStore } from "./types";

import CreateForm from "./CreateForm.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    templateId: string;
}
const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
objectStoreTemplatesStore.fetchTemplates();

const { goToIndex } = useInstanceRouting();

const props = defineProps<Props>();

const template = computed(() => objectStoreTemplatesStore.getLatestTemplate(props.templateId));

const breadcrumbItems = computed(() => [
    { title: "User Preferences", to: "/user" },
    { title: "Storage Locations", to: "/object_store_instances/index" },
    { title: "Create New", to: "/object_store_instances/create" },
    { title: template.value?.name || "Option" },
]);

async function onCreated(objectStore: UserConcreteObjectStore) {
    const message = `Created storage location ${objectStore.name}`;
    goToIndex({ message });
}
</script>

<template>
    <div>
        <div class="d-flex">
            <BreadcrumbHeading :items="breadcrumbItems" />
        </div>

        <BAlert v-if="!template" variant="info" show>
            <LoadingSpan :message="localize('Loading storage location options')" />
        </BAlert>
        <CreateForm v-else :template="template" @created="onCreated"></CreateForm>
    </div>
</template>
