<script setup lang="ts">
import { BAlert, BButton, BFormInput } from "bootstrap-vue";
import { faNetworkWired } from "font-awesome-6";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import {
    FileSourcesValidFilters,
    type FileSourceTypes,
    type FileSourceTypesDetail,
    templateTypes,
} from "@/api/fileSources";
import { Toast } from "@/composables/toast";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import Filtering from "@/utils/filtering";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import Heading from "@/components/Common/Heading.vue";
import SourceTemplateCard from "@/components/ConfigTemplates/SourceTemplateCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const breadcrumbItems = [
    { title: "User Preferences", to: "/user" },
    { title: "Remote File Sources", to: "/file_source_instances/index" },
    { title: "Create New" },
];
type AvailableTypes = { type: FileSourceTypes } & FileSourceTypesDetail[keyof FileSourceTypesDetail];

const router = useRouter();

const fileSourceTemplatesStore = useFileSourceTemplatesStore();
fileSourceTemplatesStore.ensureTemplates();

const filterText = ref("");
const templates = computed(() => fileSourceTemplatesStore.latestTemplates);
const templatesFilter = computed(() => new Filtering(FileSourcesValidFilters, undefined));
const typesAvailable = computed(() => {
    const availableTypes: AvailableTypes[] = [];

    for (const [key, value] of Object.entries(templateTypes)) {
        if (templates.value.some((t) => t.type === key)) {
            availableTypes.push({ type: key as FileSourceTypes, icon: value.icon, message: value.message });
        }
    }

    return availableTypes;
});
const filterActivated = computed(() => (t?: FileSourceTypes | "*") => {
    return (
        (t === "*" && !templatesFilter.value.getFilterValue(filterText.value, "type")) ||
        (t && templatesFilter.value.getFilterValue(filterText.value, "type") === t)
    );
});
const filteredTemplates = computed(() => {
    return templates.value.filter((tp) => {
        return (
            filterText.value === "" ||
            tp.name?.toLowerCase().includes(filterText.value.toLowerCase()) ||
            tp.type === templatesFilter.value.getFilterValue(filterText.value, "type")
        );
    });
});

function onTypeFilter(t?: FileSourceTypes | "*") {
    if (t === "*") {
        filterText.value = templatesFilter.value.setFilterValue(
            filterText.value,
            "type",
            templatesFilter.value.getFilterValue(filterText.value, "type")
        );
    } else {
        filterText.value = templatesFilter.value.setFilterValue(filterText.value, "type", t);
    }
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

function getTypeIcon(t: FileSourceTypes) {
    return templateTypes[t].icon ?? faNetworkWired;
}
</script>

<template>
    <div class="file-source-templates">
        <div class="file-source-templates-list-header">
            <BreadcrumbHeading :items="breadcrumbItems" />
        </div>

        <div class="file-source-templates-search">
            <Heading h2 size="sm">
                Select file source template to create new file sources with. These templates are configured by your
                Galaxy administrator.
            </Heading>

            <BFormInput v-model="filterText" placeholder="search templates" />

            <div class="file-source-templates-type-filter">
                Filter by type:
                <BButton
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    variant="outline-primary"
                    title="Show all templates"
                    :pressed="filterActivated('*')"
                    @click="onTypeFilter('*')">
                    All
                </BButton>

                <BButton
                    v-for="availableType in typesAvailable"
                    :key="`file-source-templates-type-${availableType.type}`"
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    variant="outline-primary"
                    :title="`Filter by file sources of type ${availableType.type}`"
                    :pressed="filterActivated(availableType.type)"
                    @click="onTypeFilter(availableType.type)">
                    <FontAwesomeIcon :icon="availableType.icon" />
                    <span class="file-source-templates-type-label">
                        {{ availableType.type }}
                    </span>
                </BButton>
            </div>
        </div>

        <BAlert v-if="fileSourceTemplatesStore.loading" variant="info" show>
            <LoadingSpan message="Loading templates" />
        </BAlert>
        <BAlert v-else-if="!filterText && filteredTemplates.length === 0" variant="info" show>
            No templates found.
        </BAlert>
        <BAlert v-else-if="filterText && filteredTemplates.length === 0" variant="info" show>
            No templates found matching <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>
        <div v-else class="file-source-templates-cards-list">
            <SourceTemplateCard
                v-for="tp in filteredTemplates"
                :key="tp.id"
                :source-template="tp"
                :select-route="`/file_source_templates/${tp.id}/new`"
                :template-types="templateTypes">
                <template v-slot:badges>
                    <div class="file-source-template-card-header-type">
                        <BButton
                            v-b-tooltip.hover.noninteractive
                            variant="outline-primary"
                            size="sm"
                            :title="templateTypes[tp.type].message + ' (click to filter by this type)'"
                            class="inline-icon-button"
                            @click="onTypeFilter(tp.type)">
                            <FontAwesomeIcon :icon="getTypeIcon(tp.type)" />
                            <span class="file-source-templates-type-label">
                                {{ tp.type }}
                            </span>
                        </BButton>
                    </div>
                </template>
            </SourceTemplateCard>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.file-source-templates {
    .file-source-templates-search {
        margin-bottom: 1rem;

        .file-source-templates-type-filter {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
    }

    .file-source-templates-cards-list {
        container: templates-list / inline-size;

        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
    }

    .file-source-templates-type-label {
        text-transform: uppercase;
    }

    .file-source-template-card-header-type {
        display: flex;
        align-self: start;
        justify-content: flex-end;
    }
}
</style>
