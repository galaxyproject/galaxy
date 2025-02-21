<script lang="ts" setup>
import { BAlert, BFormInput } from "bootstrap-vue";
import type { IconDefinition } from "font-awesome-6";
import { faNetworkWired } from "font-awesome-6";
import { computed, ref } from "vue";

import type { FileSourceTemplateSummaries } from "@/api/fileSources";
import type { ObjectStoreTemplateSummaries } from "@/api/objectStores.templates";
import type { BreadcrumbItem } from "@/components/Common/index";
import Filtering, { type ValidFilter } from "@/utils/filtering";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import SourceOptionCard from "@/components/ConfigTemplates/SourceOptionCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface SourceOptionType {
    message: string;
    icon: IconDefinition;
}

const props = defineProps<{
    title: string;
    listId: string;
    loading: boolean;
    gridView: boolean;
    routePath: string;
    breadcrumbItems: BreadcrumbItem[];
    optionTypes: Record<string, SourceOptionType>;
    validFilters: Record<string, ValidFilter<any>>;
    templates: FileSourceTemplateSummaries | ObjectStoreTemplateSummaries;
}>();

const filterText = ref("");

const templatesFilter = computed(() => new Filtering(props.validFilters, undefined));
const filteredTemplates = computed(() => {
    return props.templates.filter((tp) => {
        return (
            filterText.value === "" ||
            tp.name?.toLowerCase().includes(filterText.value.toLowerCase()) ||
            tp.type === templatesFilter.value.getFilterValue(filterText.value, "type")
        );
    });
});

function getOptionType(type: string) {
    const optionType = props.optionTypes[type];
    return {
        title: optionType?.message ?? type,
        icon: optionType?.icon ?? faNetworkWired,
    };
}
</script>

<template>
    <div class="source-options-list">
        <div class="source-options-list-header">
            <BreadcrumbHeading :items="breadcrumbItems" />
        </div>

        <div class="source-options-list-search">
            <Heading h2 size="sm">
                Select ${{ title }} to create new sources. These options are configured by your Galaxy administrator.
            </Heading>

            <BFormInput v-model="filterText" :placeholder="`Search ${title}`" />

            <ListHeader :list-id="listId" show-view-toggle />
        </div>

        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan message="Loading options" />
        </BAlert>
        <BAlert v-else-if="!filterText && filteredTemplates.length === 0" variant="info" show>
            No options found.
        </BAlert>
        <BAlert v-else-if="filterText && filteredTemplates.length === 0" variant="info" show>
            No options found matching <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>
        <div v-else class="source-options-list-cards">
            <SourceOptionCard
                v-for="tp in filteredTemplates"
                :key="tp.id"
                :source-option="tp"
                :option-type="getOptionType(tp.type)"
                :grid-view="gridView"
                :select-route="`/${routePath}/${tp.id}/new`">
                <template v-slot:badges>
                    <slot name="card-badges" :template="tp" />
                </template>
            </SourceOptionCard>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.source-options-list {
    .source-options-list-search {
        margin-bottom: 1rem;
    }

    .source-options-list-cards {
        container: templates-list / inline-size;
        display: flex;
        flex-wrap: wrap;
    }
}
</style>
