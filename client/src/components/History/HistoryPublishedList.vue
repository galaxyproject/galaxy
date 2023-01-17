<script setup>
import UtcDate from "components/UtcDate";
import Tags from "components/Common/Tags";
import { computed, ref, watch } from "vue";
import Heading from "components/Common/Heading";
import LoadingSpan from "components/LoadingSpan";
import DebouncedInput from "components/DebouncedInput";
import { getPublishedHistories, updateTags } from "./services";
import Filtering, { contains, expandNameTag } from "utils/filtering";

const validFilters = {
    name: contains("name"),
    annotation: contains("annotation"),
    tag: contains("tags", "tag", expandNameTag),
};

const filters = new Filtering(validFilters, false);

const limit = ref(50);
const offset = ref(0);
const items = ref([]);
const perPage = ref(50);
const message = ref(null);
const loading = ref(true);
const sortDesc = ref(true);
const currentPage = ref(1);
const filterText = ref("");
const showAdvanced = ref(false);
const sortBy = ref("update_time");

const noItems = computed(() => !loading.value && items.value.length === 0 && !filterText.value);
const noResults = computed(() => !loading.value && items.value.length === 0 && filterText.value);

const fields = [
    { key: "name", sortable: true },
    { key: "annotation", sortable: false },
    { label: "Owner", key: "username", sortable: false },
    { label: "Community Tags", key: "tags", sortable: false },
    { label: "Last Updated", key: "update_time", sortable: true },
];

const localFilter = computed({
    get() {
        return filterText.value;
    },
    set(newVal) {
        if (newVal !== filterText.value) {
            updateFilter(newVal);
        }
    },
});

const filterSettings = computed(() => filters.toAlias(filters.getFilters(filterText.value)));

const updateFilter = (newVal, append = false) => {
    let oldValue = filterText.value;
    if (append) {
        oldValue += newVal;
    } else {
        oldValue = newVal;
    }
    filterText.value = oldValue.trim();
};

const onTagClick = (tag) => {
    if (filterText.value.includes("tag:" + tag.label)) {
        updateFilter(filterText.value.replace("tag:" + tag.label, ""));
    } else {
        if (filterText.value.length === 0) {
            updateFilter("tag:" + tag.label, true);
        } else {
            updateFilter(" tag:" + tag.label, true);
        }
    }
};

const load = async () => {
    loading.value = true;

    getPublishedHistories(
        {
            limit: limit.value,
            offset: offset.value,
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
            filterText: filterText.value,
        },
        filters
    )
        .then((data) => {
            items.value = data;
        })
        .catch((error) => {
            message.value = error;
        })
        .finally(() => {
            loading.value = false;
        });
};

const onTagsUpdate = (newTags, row) => {
    row.item.tags = newTags;
    updateTags(row.item.id, "History", row.item.tags);
};

const onToggle = () => {
    showAdvanced.value = !showAdvanced.value;
};

const onSearch = () => {
    onToggle();
    updateFilter(filters.getFilterText(filterSettings.value));
};

load();

watch([filterText, sortBy, sortDesc], () => {
    load();
});
</script>

<template>
    <section id="published-histories" class="d-flex flex-column">
        <Heading h1>Published Histories</Heading>

        <b-alert v-if="noItems" variant="info" show>No published histories found.</b-alert>

        <div v-else>
            <b-input-group class="mb-2">
                <DebouncedInput v-slot="{ value, input }" v-model="localFilter">
                    <b-form-input
                        id="published-histories-filter"
                        size="sm"
                        :class="filterText && 'font-weight-bold'"
                        :value="value"
                        :placeholder="'Search name, annotation and tags' | localize"
                        title="clear search (esc)"
                        data-description="filter text input"
                        @input="input"
                        @keyup.esc="updateFilter('')" />
                </DebouncedInput>
                <b-input-group-append>
                    <b-button
                        id="published-histories-advanced-filter-toggle"
                        size="sm"
                        :pressed="showAdvanced"
                        :variant="showAdvanced ? 'info' : 'secondary'"
                        title="show advanced filter"
                        data-description="show advanced filter toggle"
                        aria-label="Show advanced filter"
                        @click="onToggle">
                        <icon v-if="showAdvanced" icon="angle-double-up" />
                        <icon v-else icon="angle-double-down" />
                    </b-button>
                    <b-button
                        size="sm"
                        aria-label="Clear filters"
                        data-description="clear filters"
                        @click="updateFilter('')">
                        <icon icon="times" />
                    </b-button>
                </b-input-group-append>
            </b-input-group>

            <div v-if="showAdvanced" class="mt-2" @keyup.esc="onToggle" @keyup.enter="onSearch">
                <small>Filter by name:</small>
                <b-form-input
                    id="published-histories-advanced-filter-name"
                    v-model="filterSettings['name:']"
                    size="sm"
                    placeholder="any name" />
                <small class="mt-1">Filter by annotation:</small>
                <b-form-input v-model="filterSettings['annotation:']" size="sm" placeholder="any annotation" />
                <small class="mt-1">Filter by community tag:</small>
                <b-form-input
                    id="published-histories-advanced-filter-tag"
                    v-model="filterSettings['tag:']"
                    size="sm"
                    placeholder="any community tag" />
                <div class="mt-3">
                    <b-button
                        id="published-histories-advanced-filter-submit"
                        class="mr-1"
                        size="sm"
                        variant="primary"
                        description="apply filters"
                        @click="onSearch">
                        <icon icon="search" />
                        <span>{{ "Search" | localize }}</span>
                    </b-button>
                    <b-button size="sm" @click="onToggle">
                        <icon icon="redo" />
                        <span>{{ "Cancel" | localize }}</span>
                    </b-button>
                </div>
            </div>

            <b-alert v-if="noResults" variant="info" show>
                No matching entries found for: <span class="font-weight-bold">{{ filterText }}</span>
            </b-alert>

            <b-alert v-if="loading" variant="info" show>
                <LoadingSpan message="Loading published histories" />
            </b-alert>

            <b-table
                v-if="items.length"
                id="published-histories-table"
                no-local-sorting
                striped
                :fields="fields"
                :items="items"
                :per-page="perPage"
                :current-page="currentPage"
                :sort-by.sync="sortBy"
                :sort-desc.sync="sortDesc">
                <template v-slot:cell(name)="row">
                    <router-link :to="`/published/history?id=${row.item.id}`">
                        {{ row.item.name }}
                    </router-link>
                </template>
                <template v-slot:cell(tags)="row">
                    <Tags
                        :index="row.index"
                        :tags="row.item.tags"
                        @tag-click="onTagClick"
                        @input="onTagsUpdate($event, row)" />
                </template>

                <template v-slot:cell(update_time)="data">
                    <UtcDate :date="data.value" mode="elapsed" />
                </template>
            </b-table>

            <b-pagination
                v-if="items.length > perPage"
                v-model="currentPage"
                :per-page="perPage"
                :total-rows="items.length"
                align="center" />
        </div>
    </section>
</template>
