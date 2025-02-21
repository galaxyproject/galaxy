<script lang="ts" setup>
import { BAlert, BFormInput } from "bootstrap-vue";
import { faNetworkWired } from "font-awesome-6";
import { computed, ref } from "vue";

import type { ObjectStoreTypes } from "@/api/objectStores.templates";
import { objectStoreTemplateTypes, ObjectStoreValidFilters } from "@/api/objectStores.templates";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import { useUserStore } from "@/stores/userStore";
import Filtering from "@/utils/filtering";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import SourceOptionCard from "@/components/ConfigTemplates/SourceOptionCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";

const breadcrumbItems = [
    { title: "User Preferences", to: "/user" },
    { title: "Storage Locations", to: "/object_store_instances/index" },
    { title: "Create New" },
];

const userStore = useUserStore();

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
objectStoreTemplatesStore.ensureTemplates();

const filterText = ref("");

const currentListView = computed(() => userStore.currentListViewPreferences.objectStoreOptions || "grid");

const templates = computed(() => objectStoreTemplatesStore.latestTemplates);
const templatesFilter = computed(() => new Filtering(ObjectStoreValidFilters, undefined));
const filteredTemplates = computed(() => {
    return templates.value.filter((tp) => {
        return (
            filterText.value === "" ||
            tp.name?.toLowerCase().includes(filterText.value.toLowerCase()) ||
            tp.type === templatesFilter.value.getFilterValue(filterText.value, "type")
        );
    });
});

function getOptionType(opType: ObjectStoreTypes) {
    return {
        title: objectStoreTemplateTypes[opType].message,
        icon: objectStoreTemplateTypes[opType].icon ?? faNetworkWired,
    };
}
</script>

<template>
    <div class="user-object-store-templates">
        <div class="user-object-store-templates-list-header">
            <BreadcrumbHeading :items="breadcrumbItems" />
        </div>

        <div class="user-object-store-templates-search">
            <Heading h2 size="sm">
                Select a storage location option to create new storage location. These options are configured by your
                Galaxy administrator.
            </Heading>

            <BFormInput v-model="filterText" placeholder="Search options" />

            <ListHeader list-id="objectStoreOptions" show-view-toggle />
        </div>

        <BAlert v-if="objectStoreTemplatesStore.loading" variant="info" show>
            <LoadingSpan message="Loading options" />
        </BAlert>
        <BAlert v-else-if="!filterText && filteredTemplates.length === 0" variant="info" show>
            No options found.
        </BAlert>
        <BAlert v-else-if="filterText && filteredTemplates.length === 0" variant="info" show>
            No options found matching <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>
        <div v-else class="user-object-store-templates-cards-list">
            <SourceOptionCard
                v-for="tp in filteredTemplates"
                :key="tp.id"
                :source-option="tp"
                :option-type="getOptionType(tp.type)"
                :grid-view="currentListView === 'grid'"
                :select-route="`/object_store_templates/${tp.id}/new`">
                <template v-slot:badges>
                    <ObjectStoreBadges :badges="tp.badges" size="lg" />
                </template>
            </SourceOptionCard>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
@import "_breakpoints.scss";

.user-object-store-templates {
    .user-object-store-templates-search {
        margin-bottom: 1rem;
    }

    .user-object-store-templates-cards-list {
        container: templates-list / inline-size;

        display: flex;
        flex-wrap: wrap;
    }
}
</style>
