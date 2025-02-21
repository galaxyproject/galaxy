<script setup lang="ts">
import { BAlert, BFormInput } from "bootstrap-vue";
import { faNetworkWired } from "font-awesome-6";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { FileSourcesValidFilters, type FileSourceTypes, templateTypes } from "@/api/fileSources";
import { Toast } from "@/composables/toast";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { useUserStore } from "@/stores/userStore";
import Filtering from "@/utils/filtering";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import SourceOptionCard from "@/components/ConfigTemplates/SourceOptionCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const breadcrumbItems = [
    { title: "User Preferences", to: "/user" },
    { title: "Remote File Sources", to: "/file_source_instances/index" },
    { title: "Create New" },
];

const userStore = useUserStore();

const router = useRouter();

const fileSourceTemplatesStore = useFileSourceTemplatesStore();
fileSourceTemplatesStore.ensureTemplates();

const filterText = ref("");

const currentListView = computed(() => userStore.currentListViewPreferences.fileSourceOptions || "grid");

const templates = computed(() => fileSourceTemplatesStore.latestTemplates);
const templatesFilter = computed(() => new Filtering(FileSourcesValidFilters, undefined));
const filteredTemplates = computed(() => {
    return templates.value.filter((tp) => {
        return (
            filterText.value === "" ||
            tp.name?.toLowerCase().includes(filterText.value.toLowerCase()) ||
            tp.type === templatesFilter.value.getFilterValue(filterText.value, "type")
        );
    });
});

function getOptionType(opType: FileSourceTypes) {
    return { title: templateTypes[opType].message, icon: templateTypes[opType].icon ?? faNetworkWired };
}

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

handleOAuth2Redirect();
</script>

<template>
    <div class="file-source-templates">
        <div class="file-source-templates-list-header">
            <BreadcrumbHeading :items="breadcrumbItems" />
        </div>

        <div class="file-source-templates-search">
            <Heading h2 size="sm">
                Select a file source option to create new file sources. These options are configured by your Galaxy
                administrator.
            </Heading>

            <BFormInput v-model="filterText" placeholder="Search options" />

            <ListHeader list-id="fileSourceOptions" show-view-toggle />
        </div>

        <BAlert v-if="fileSourceTemplatesStore.loading" variant="info" show>
            <LoadingSpan message="Loading options" />
        </BAlert>
        <BAlert v-else-if="!filterText && filteredTemplates.length === 0" variant="info" show>
            No options found.
        </BAlert>
        <BAlert v-else-if="filterText && filteredTemplates.length === 0" variant="info" show>
            No options found matching <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>
        <div v-else class="file-source-templates-cards-list">
            <SourceOptionCard
                v-for="tp in filteredTemplates"
                :key="tp.id"
                :source-option="tp"
                :option-type="getOptionType(tp.type)"
                :grid-view="currentListView === 'grid'"
                :select-route="`/file_source_templates/${tp.id}/new`"
                :template-types="templateTypes" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.file-source-templates {
    .file-source-templates-search {
        margin-bottom: 1rem;
    }

    .file-source-templates-cards-list {
        container: templates-list / inline-size;

        display: flex;
        flex-wrap: wrap;
    }
}
</style>
