<script lang="ts" setup>
import { computed } from "vue";

import { objectStoreTemplateTypes, ObjectStoreValidFilters } from "@/api/objectStores.templates";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import { useUserStore } from "@/stores/userStore";

import SourceOptionsList from "@/components/ConfigTemplates/SourceOptionsList.vue";

const breadcrumbItems = [
    { title: "User Preferences", to: "/user" },
    { title: "Storage Locations", to: "/object_store_instances/index" },
    { title: "Create New" },
];

const userStore = useUserStore();

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
objectStoreTemplatesStore.ensureTemplates();

const currentListView = computed(() => userStore.currentListViewPreferences.objectStoreOptions || "grid");
const templates = computed(() => objectStoreTemplatesStore.latestTemplates);
</script>

<template>
    <SourceOptionsList
        title="storage location option"
        list-id="objectStoreOptions"
        show-badges
        :grid-view="currentListView === 'grid'"
        route-path="object_store_templates"
        :breadcrumb-items="breadcrumbItems"
        :loading="objectStoreTemplatesStore.loading"
        :option-types="objectStoreTemplateTypes"
        :valid-filters="ObjectStoreValidFilters"
        :templates="templates" />
</template>
