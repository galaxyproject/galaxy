<script setup lang="ts">
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useResizeObserver } from "@vueuse/core";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import localize from "@/utils/localization";

import type { FieldFilter, FilterOption } from "./configs/types";
import type { ColumnFilterChip } from "./useColumnFilters";

import GBadge from "@/components/BaseComponents/GBadge.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GDropdown from "@/components/BaseComponents/GDropdown.vue";
import GDropdownItem from "@/components/BaseComponents/GDropdownItem.vue";

const props = defineProps<{
    chips: ColumnFilterChip[];
    /** Keep the chips on one line: as many as fit, the rest in a "+N more" menu, with a Clear link */
    inline?: boolean;
}>();

const emit = defineEmits<{
    (e: "remove", filter: FieldFilter, option: FilterOption): void;
    /** Remove every chip; only offered inline */
    (e: "clear"): void;
}>();

/** The whole chip area, which takes the width its parent gives it */
const root = ref<HTMLElement>();
/** The chips' own line; only it clips, so the "+N more" menu can open below it */
const line = ref<HTMLElement>();
/** How many chips fit on the line; the rest are in the "+N more" menu. All of them unless inline */
const shownCount = ref(Infinity);

const shownChips = computed(() => props.chips.slice(0, shownCount.value));
const hiddenChips = computed(() => props.chips.slice(shownCount.value));

function chipKey(chip: ColumnFilterChip) {
    return `${chip.filter.key}-${chip.option.id}`;
}

function chipLabel(chip: ColumnFilterChip) {
    return `${chip.title}: ${chip.option.name}`;
}

/** Show all chips, then drop the last one until the line no longer overflows */
async function fit() {
    if (!props.inline) {
        return;
    }
    shownCount.value = props.chips.length;
    await nextTick();
    while (line.value && shownCount.value > 1 && line.value.scrollWidth > line.value.clientWidth) {
        shownCount.value--;
        await nextTick();
    }
}

// the line is sized by its chips, so watch the area around it for more or less room
useResizeObserver(root, fit);
// the chips array is rebuilt on any filter change, so only refit when the chips themselves change
watch(() => props.chips.map(chipKey).join(" "), fit);
// also covers browsers (and tests) without ResizeObserver
onMounted(fit);
</script>

<template>
    <div
        v-if="chips.length > 0"
        ref="root"
        class="d-flex align-items-center"
        :class="{ 'column-filter-chips-inline': inline }"
        data-description="grid active column filters">
        <div ref="line" class="column-filter-chips-line d-flex align-items-center">
            <GBadge
                v-for="chip in shownChips"
                :key="chipKey(chip)"
                class="column-filter-chip"
                button
                pill
                variant="info"
                :title="`${localize('Remove this filter')}: ${chipLabel(chip)}`"
                :data-description="`grid active column filter ${chip.filter.key}`"
                :data-option-id="chip.option.id"
                @click="emit('remove', chip.filter, chip.option)">
                <span class="column-filter-chip-key">{{ `${chip.title}: ` }}</span>
                <span class="column-filter-chip-name">{{ chip.option.name }}</span>
                <FontAwesomeIcon :icon="faTimes" class="column-filter-chip-remove" />
            </GBadge>
        </div>
        <GDropdown
            v-if="hiddenChips.length > 0"
            class="flex-shrink-0 column-filter-chips-dropdown"
            :text="`+${hiddenChips.length} more`"
            toggle-class="text-decoration-none"
            variant="link"
            size="sm"
            right
            data-description="grid hidden column filters">
            <GDropdownItem
                v-for="chip in hiddenChips"
                :key="chipKey(chip)"
                :title="`${localize('Remove this filter')}: ${chipLabel(chip)}`"
                :data-description="`grid hidden column filter ${chip.filter.key}`"
                :data-option-id="chip.option.id"
                @click="emit('remove', chip.filter, chip.option)">
                {{ chipLabel(chip) }}
                <FontAwesomeIcon :icon="faTimes" class="ml-1" />
            </GDropdownItem>
        </GDropdown>
        <GButton
            v-if="inline"
            class="flex-shrink-0"
            size="small"
            transparent
            color="grey"
            :title="localize('Remove all column filters')"
            data-description="grid clear column filters"
            @click="emit('clear')">
            {{ localize("Clear") }}
        </GButton>
    </div>
</template>

<style scoped lang="scss">
.column-filter-chips-line {
    flex-wrap: wrap;
    gap: 0.25rem;
}

.column-filter-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    max-width: 16rem;
    padding: 0.35em 0.6em 0.35em 0.75em;

    &.g-badge:hover {
        text-decoration: none;
    }

    .column-filter-chip-key {
        flex: none;
        font-weight: normal;
        opacity: 0.8;
    }

    .column-filter-chip-name {
        overflow: hidden;
        text-overflow: ellipsis;
        min-width: 0;
    }

    .column-filter-chip-remove {
        flex: none;
        font-size: 0.85em;
    }
}

.column-filter-chips-inline {
    gap: 0.25rem;
    min-width: 0;

    .column-filter-chips-line {
        flex-wrap: nowrap;
        min-width: 0;
        overflow: hidden;
        // room for the chips' focus outlines
        padding: 0.125rem;
    }

    .column-filter-chip {
        flex: none;

        // a lone chip shrinks rather than overflowing
        &:only-child {
            flex: 0 1 auto;
            min-width: 0;
        }
    }
}

.column-filter-chips-dropdown {
    :deep(.dropdown-item) {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
}
</style>
