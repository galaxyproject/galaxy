<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router/composables";

import { FileSourcesValidFilters, templateTypes } from "@/api/fileSources";
import { Toast } from "@/composables/toast";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { useUserStore } from "@/stores/userStore";

import SourceOptionsList from "@/components/ConfigTemplates/SourceOptionsList.vue";

const breadcrumbItems = [
    { title: "User Preferences", to: "/user" },
    { title: "My Repositories", to: "/file_source_instances/index" },
    { title: "Create New" },
];

const userStore = useUserStore();
const router = useRouter();
const fileSourceTemplatesStore = useFileSourceTemplatesStore();

const currentListView = computed(() => userStore.currentListViewPreferences.fileSourceOptions || "grid");
const templates = computed(() => fileSourceTemplatesStore.latestTemplates);

function handleOAuth2Redirect() {
    const { error } = router.currentRoute.query;

    if (error) {
        if (error === "access_denied") {
            Toast.error("You must authorize Galaxy to access this resource. Please try again.");
        } else {
            const errorMessage = Array.isArray(error) ? error[0] : error;

            Toast.error(errorMessage || "There was an error creating the file source.");
        }
    }
}

onMounted(() => {
    fileSourceTemplatesStore.ensureTemplates();
    handleOAuth2Redirect();
});
</script>

<template>
    <SourceOptionsList
        title="file source option"
        list-id="fileSourceOptions"
        :loading="fileSourceTemplatesStore.loading"
        :grid-view="currentListView === 'grid'"
        route-path="file_source_templates"
        :breadcrumb-items="breadcrumbItems"
        :option-types="templateTypes"
        :valid-filters="FileSourcesValidFilters"
        :templates="templates" />
</template>
