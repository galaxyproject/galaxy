<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faUserGear } from "font-awesome-6";
import { computed } from "vue";
import { RouterLink } from "vue-router";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import { useInstanceRouting } from "./routing";
import type { UserConcreteObjectStore } from "./types";

import CreateForm from "./CreateForm.vue";
import Heading from "@/components/Common/Heading.vue";
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
        <div class="d-flex">
            <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">
                <RouterLink to="/user">
                    <FontAwesomeIcon v-b-tooltip.hover.noninteractive :icon="faUserGear" title="User preferences" />
                </RouterLink>
                /
                <RouterLink to="/object_store_instances/index"> Storage Locations</RouterLink> /
                <RouterLink to="/object_store_instances/create"> Templates</RouterLink>
                / {{ template?.name || "Template" }}
            </Heading>
        </div>

        <LoadingSpan v-if="!template" message="Loading storage location templates" />
        <CreateForm v-else :template="template" @created="onCreated"></CreateForm>
    </div>
</template>
