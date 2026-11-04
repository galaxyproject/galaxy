<script setup lang="ts">
import { faFilter } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { watchDebounced } from "@vueuse/core";
import { computed, nextTick, ref } from "vue";

import localize from "@/utils/localization";

import type { FieldFilter, FilterOption } from "./configs/types";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownForm from "@/components/BaseComponents/GDropdownForm.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import UtcDate from "@/components/UtcDate.vue";

interface Props {
    filter: FieldFilter;
    /** Column title, used in the toggle's accessible name */
    title: string;
    selected: FilterOption[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:selected", options: FilterOption[]): void;
}>();

const query = ref("");
const results = ref<FilterOption[]>([]);
const loading = ref(false);
const errorMessage = ref("");
const searchInput = ref<HTMLInputElement>();
let searched = false;
let latestSearch = 0;

const selectedIds = computed(() => new Set(props.selected.map((option) => option.id)));

/** Selected items stay on top, whatever the search text */
const options = computed(() => [
    ...props.selected,
    ...results.value.filter((option) => !selectedIds.value.has(option.id)),
]);

async function search() {
    const searchId = ++latestSearch;
    loading.value = true;
    try {
        const found = await props.filter.search(query.value.trim());
        if (searchId === latestSearch) {
            results.value = found;
            errorMessage.value = "";
        }
    } catch (e) {
        if (searchId === latestSearch) {
            errorMessage.value = `Failed to load ${props.filter.plural}: ${e}`;
        }
    } finally {
        if (searchId === latestSearch) {
            loading.value = false;
        }
    }
}

watchDebounced(query, search, { debounce: 300 });

async function onShow() {
    if (!searched) {
        searched = true;
        search();
    }
    await nextTick();
    searchInput.value?.focus();
}

function toggle(option: FilterOption) {
    if (selectedIds.value.has(option.id)) {
        emit(
            "update:selected",
            props.selected.filter((selectedOption) => selectedOption.id !== option.id),
        );
    } else {
        emit("update:selected", [...props.selected, option]);
    }
}
</script>

<template>
    <GDropdown
        variant="link"
        size="sm"
        no-caret
        lazy
        toggle-class="grid-column-filter-toggle p-0 ml-1"
        menu-class="grid-column-filter-menu"
        :aria-label="localize(`Filter by ${title.toLowerCase()}`)"
        :data-description="`grid column filter ${filter.key}`"
        @show="onShow">
        <template v-slot:button-content>
            <FontAwesomeIcon :icon="faFilter" :class="selected.length ? 'text-primary' : 'text-muted'" fixed-width />
            <span v-if="selected.length" class="badge badge-primary" data-description="grid column filter count">
                {{ selected.length }}
            </span>
        </template>
        <GDropdownForm form-class="p-2">
            <input
                ref="searchInput"
                v-model="query"
                class="form-control form-control-sm mb-2"
                type="search"
                :placeholder="localize(`search ${filter.plural}`)"
                :aria-label="localize(`Search ${filter.plural}`)"
                data-description="grid column filter search" />
            <div class="grid-column-filter-options">
                <GCheckbox
                    v-for="option in options"
                    :key="option.id"
                    class="grid-column-filter-option"
                    :model-value="selectedIds.has(option.id)"
                    :data-description="`grid column filter option ${option.id}`"
                    @update:model-value="toggle(option)">
                    <span class="d-block font-weight-bold text-break">{{ option.name }}</span>
                    <small v-if="option.detail?.() || option.updateTime" class="d-block text-muted">
                        <span v-if="option.detail?.()">{{ option.detail() }}</span>
                        <span v-if="option.detail?.() && option.updateTime"> · </span>
                        <span v-if="option.updateTime"
                            >updated <UtcDate :date="option.updateTime" mode="elapsed"
                        /></span>
                    </small>
                </GCheckbox>
                <LoadingSpan v-if="loading" class="d-block small" :message="localize(`Loading ${filter.plural}`)" />
                <div v-else-if="errorMessage" class="small text-danger">{{ errorMessage }}</div>
                <div v-else-if="options.length === 0" class="small text-muted">
                    <span v-if="query.trim()">{{ localize(`No ${filter.plural} match "${query.trim()}"`) }}</span>
                    <span v-else>{{ localize(`No ${filter.plural} found`) }}</span>
                </div>
            </div>
            <GButton
                v-if="selected.length"
                class="mt-2"
                size="small"
                outline
                color="blue"
                data-description="grid column filter clear"
                @click="emit('update:selected', [])">
                {{ localize("Clear") }}
            </GButton>
        </GDropdownForm>
    </GDropdown>
</template>

<style scoped lang="scss">
:deep(.grid-column-filter-menu) {
    width: 22rem;
}

.grid-column-filter-options {
    max-height: 20rem;
    overflow-y: auto;
}

.grid-column-filter-option {
    display: flex;
    align-items: flex-start;
    padding: 0.25rem 0;
}
</style>
