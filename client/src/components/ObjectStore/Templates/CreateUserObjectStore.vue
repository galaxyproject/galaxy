<script lang="ts" setup>
import { computed } from "vue";

import { objectStoreTemplateTypes, ObjectStoreValidFilters } from "@/api/objectStores.templates";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import { useUserStore } from "@/stores/userStore";

import SourceOptionsList from "@/components/ConfigTemplates/SourceOptionsList.vue";

const breadcrumbItems = [
    { title: "用户偏好", to: "/user" },
    { title: "存储位置", to: "/object_store_instances/index" },
    { title: "创建新存储" },
];

const userStore = useUserStore();

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
objectStoreTemplatesStore.ensureTemplates();

const currentListView = computed(() => userStore.currentListViewPreferences.objectStoreOptions || "grid");
const templates = computed(() => objectStoreTemplatesStore.latestTemplates);
</script>

<template>
    <SourceOptionsList
        title="存储位置选项"
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
