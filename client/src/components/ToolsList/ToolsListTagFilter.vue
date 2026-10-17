<script setup lang="ts">
import { faTags } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import ToolFilterChip from "./ToolFilterChip.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownGroup from "@/components/BaseComponents/GDropdownGroup.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";
import GDropdownText from "@/components/BaseComponents/GDropdownText.vue";

const props = defineProps<{
    tags: string[];
    selectedTags: string[];
    disabled?: boolean;
    loading?: boolean;
}>();

const emit = defineEmits<{
    (e: "toggle-tag", tag: string): void;
}>();

const search = ref("");
const matches = computed(() => {
    const query = search.value.trim().toLowerCase();
    const selected = new Set(props.selectedTags);
    return props.tags.filter((tag) => !selected.has(tag) && tag.toLowerCase().includes(query));
});
const visibleTags = computed(() => matches.value.slice(0, 100));
</script>

<template>
    <div class="d-flex flex-wrap align-items-center flex-gapx-1 flex-gapy-1">
        <GDropdown
            :disabled="disabled"
            variant="link"
            class="tool-tags-dropdown"
            initial-focus="input"
            toggle-class="text-decoration-none"
            size="sm">
            <template v-slot:button-content>
                <span class="sr-only">Search tags/categories</span>
                <FontAwesomeIcon :icon="faTags" />
                <i> Search tags/categories </i>
            </template>

            <GDropdownText>
                <GFormInput
                    v-model="search"
                    class="w-100"
                    aria-label="Search tags/categories"
                    placeholder="Search tags/categories"
                    type="search" />
            </GDropdownText>

            <div class="tag-options">
                <GDropdownGroup aria-label="Available tags">
                    <GDropdownItem v-for="tag in visibleTags" :key="tag" @click="emit('toggle-tag', tag)">
                        {{ tag }}
                    </GDropdownItem>
                </GDropdownGroup>
                <GDropdownText v-if="loading">Loading tags/categories...</GDropdownText>
                <GDropdownText v-else-if="!matches.length">
                    {{ tags.length ? "No matching tags found." : "No tags available." }}
                </GDropdownText>
                <GDropdownText v-if="matches.length > 100" class="text-muted">
                    Showing 100 of {{ matches.length }} matches. Type to narrow your search.
                </GDropdownText>
            </div>
        </GDropdown>
        <ToolFilterChip
            v-for="tag in selectedTags"
            :key="tag"
            :label="tag"
            :value="tag"
            kind="tags"
            :remove-title="`Remove tag ${tag}`"
            :disabled="disabled"
            @remove="emit('toggle-tag', tag)" />
    </div>
</template>

<style scoped lang="scss">
.tool-tags-dropdown {
    :deep(.dropdown-menu) {
        min-width: 20rem;
        max-width: min(32rem, 90vw);
    }

    .tag-options {
        max-height: 50vh;
        overflow-y: auto;
    }

    :deep(.dropdown-item) {
        white-space: normal;
        overflow-wrap: anywhere;
    }
}
</style>
