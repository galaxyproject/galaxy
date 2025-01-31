<script lang="ts" setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormInput } from "bootstrap-vue";
import { faNetworkWired, faUserGear } from "font-awesome-6";
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import type { ObjectStoreTypes, ObjectStoreTypesDetail } from "@/api/objectStores.templates";
import { objectStoreTemplateTypes, ObjectStoreValidFilters } from "@/api/objectStores.templates";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import Filtering from "@/utils/filtering";

import Heading from "@/components/Common/Heading.vue";
import SourceTemplateCard from "@/components/ConfigTemplates/SourceTemplateCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";

type AvailableTypes = { type: ObjectStoreTypes } & ObjectStoreTypesDetail[keyof ObjectStoreTypesDetail];

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
objectStoreTemplatesStore.ensureTemplates();

const filterText = ref("");
const templates = computed(() => objectStoreTemplatesStore.latestTemplates);
const templatesFilter = computed(() => new Filtering(ObjectStoreValidFilters, undefined));
const typesAvailable = computed(() => {
    const availableTypes: AvailableTypes[] = [];

    for (const [key, value] of Object.entries(objectStoreTemplateTypes)) {
        if (templates.value.some((t) => t.type === key)) {
            availableTypes.push({ type: key as ObjectStoreTypes, icon: value.icon, message: value.message });
        }
    }

    return availableTypes;
});
const filterActivated = computed(() => (t?: ObjectStoreTypes | "*") => {
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

function onTypeFilter(t?: ObjectStoreTypes | "*") {
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

function getTypeIcon(t: ObjectStoreTypes) {
    return objectStoreTemplateTypes[t].icon ?? faNetworkWired;
}
</script>

<template>
    <div class="user-object-store-templates">
        <div class="user-object-store-templates-list-header">
            <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">
                <RouterLink to="/user">
                    <FontAwesomeIcon v-b-tooltip.hover.noninteractive :icon="faUserGear" title="User preferences" />
                </RouterLink>
                /
                <RouterLink to="/object_store_instances/index"> Storage Locations </RouterLink>
                / Templates
            </Heading>
        </div>

        <div class="user-object-store-templates-search">
            <Heading h2 size="sm">
                Select storage location template to create new storage location with. These templates are configured by
                your Galaxy administrator.
            </Heading>

            <BFormInput v-model="filterText" placeholder="search templates" />

            <div class="user-object-store-templates-type-filter">
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
                    :key="`user-object-store-templates-type-${availableType.type}`"
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    variant="outline-primary"
                    :title="`Filter by file sources of type ${availableType.type}`"
                    :pressed="filterActivated(availableType.type)"
                    @click="onTypeFilter(availableType.type)">
                    <FontAwesomeIcon :icon="availableType.icon" />
                    <span class="user-object-store-templates-type-label">
                        {{ availableType.type }}
                    </span>
                </BButton>
            </div>
        </div>

        <BAlert v-if="objectStoreTemplatesStore.loading" variant="info" show>
            <LoadingSpan message="Loading templates" />
        </BAlert>
        <BAlert v-else-if="!filterText && filteredTemplates.length === 0" variant="info" show>
            No templates found.
        </BAlert>
        <BAlert v-else-if="filterText && filteredTemplates.length === 0" variant="info" show>
            No templates found matching <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>
        <div v-else class="user-object-store-templates-cards-list">
            <SourceTemplateCard
                v-for="tp in filteredTemplates"
                :key="tp.id"
                :source-template="tp"
                :select-route="`/object_store_templates/${tp.id}/new`"
                @typeFilter="onTypeFilter">
                <template v-slot:badges>
                    <div class="user-object-store-template-card-header-type">
                        <ObjectStoreBadges :badges="tp.badges" size="lg" />

                        <BButton
                            v-b-tooltip.hover.noninteractive
                            variant="outline-primary"
                            size="sm"
                            :title="objectStoreTemplateTypes[tp.type].message + ' (click to filter by this type)'"
                            class="inline-icon-button"
                            @click="onTypeFilter(tp.type)">
                            <FontAwesomeIcon :icon="getTypeIcon(tp.type)" />
                            <span class="user-object-store-templates-type-label">
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
@import "breakpoints.scss";

.user-object-store-templates {
    .user-object-store-templates-search {
        margin-bottom: 1rem;

        .user-object-store-templates-type-filter {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
    }

    .user-object-store-templates-cards-list {
        container: templates-list / inline-size;

        display: flex;
        flex-wrap: wrap;
        gap: 1rem;

        .user-object-store-template-card-header-type {
            display: flex;
            gap: 0.1rem;
            justify-content: right;
        }
    }

    .user-object-store-templates-type-label {
        text-transform: uppercase;
    }
}
</style>
