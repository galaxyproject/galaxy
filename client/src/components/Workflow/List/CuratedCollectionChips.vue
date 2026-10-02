<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import type { CuratedWorkflowCollection } from "@/api/curatedWorkflows";
import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    collections: CuratedWorkflowCollection[];
    /** The selected collection, case-folded. */
    active?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "toggle", name: string): void;
}>();

/** How many of the given offsets share the first one's row. */
function countFirstRow(offsetTops: number[]): number {
    const first = offsetTops[0];
    return first === undefined ? 0 : offsetTops.filter((top) => Math.abs(top - first) < 1).length;
}

const container = ref<HTMLElement | null>(null);
const expanded = ref(false);
const hiddenCount = ref(0);
// Zero until measured, which leaves the row unclipped wherever there's no layout to measure.
const rowHeight = ref(0);
const moreWidth = ref(0);

const isCollapsed = computed(() => !expanded.value && rowHeight.value > 0);
const firstHiddenIndex = computed(() => props.collections.length - hiddenCount.value);
const activeIsHidden = computed(
    () =>
        isCollapsed.value &&
        props.collections.findIndex((collection) => collection.name.toLowerCase() === props.active) >=
            firstHiddenIndex.value,
);
const rowStyle = computed(() =>
    isCollapsed.value
        ? {
              maxHeight: `${rowHeight.value}px`,
              // The "+N more" button sits over the end of the first row, so keep chips out from under it.
              paddingRight: hiddenCount.value > 0 ? `${moreWidth.value}px` : undefined,
          }
        : {},
);

function isHidden(index: number) {
    return isCollapsed.value && index >= firstHiddenIndex.value;
}

function chipElements(): HTMLElement[] {
    return Array.from(container.value?.querySelectorAll<HTMLElement>(".curated-workflow-collection") ?? []);
}

function measure() {
    // While expanded every chip is visible, so there's nothing to fit; re-measure on collapse.
    if (expanded.value || !container.value) {
        return;
    }
    const chips = chipElements();
    rowHeight.value = chips[0]?.offsetHeight ?? 0;
    hiddenCount.value = chips.length - countFirstRow(chips.map((chip) => chip.offsetTop));
    const more = container.value.querySelector<HTMLElement>(".curated-workflow-collections-more");
    moreWidth.value = more ? more.offsetWidth + 4 : 0;
}

function remeasure() {
    nextTick(measure);
}

useResizeObserver(container, measure);
onMounted(remeasure);
// The reserved space for "+N more" changes the layout it was measured from, so settle it again.
watch([() => props.collections, expanded, hiddenCount, moreWidth], remeasure);
</script>

<template>
    <div
        ref="container"
        class="curated-workflow-collections d-flex flex-wrap"
        :class="{ collapsed: isCollapsed }"
        :style="rowStyle"
        role="group"
        :aria-label="localize('Filter by IWC collection')">
        <GButton
            v-for="(collection, index) in props.collections"
            :key="collection.name"
            class="curated-workflow-collection"
            :class="{ 'curated-workflow-collection-hidden': isHidden(index) }"
            :data-collection="collection.name"
            :tabindex="isHidden(index) ? -1 : undefined"
            :aria-hidden="isHidden(index) ? 'true' : undefined"
            size="small"
            color="blue"
            outline
            :pressed="props.active === collection.name.toLowerCase()"
            @click="emit('toggle', collection.name)">
            {{ collection.name }}
            <span class="curated-workflow-collection-count">{{ collection.count }}</span>
        </GButton>
        <GButton
            v-if="expanded && hiddenCount > 0"
            class="curated-workflow-collections-less"
            size="small"
            color="blue"
            transparent
            @click="expanded = false">
            {{ localize("Show fewer") }}
        </GButton>
        <GButton
            v-if="isCollapsed && hiddenCount > 0"
            class="curated-workflow-collections-more"
            size="small"
            color="blue"
            outline
            :pressed="activeIsHidden"
            :title="localize('Show all collections')"
            @click="expanded = true">
            +{{ hiddenCount }} {{ localize("more") }}
        </GButton>
    </div>
</template>

<style scoped lang="scss">
.curated-workflow-collections {
    position: relative;
    gap: 0.25rem;

    &.collapsed {
        overflow: hidden;
    }

    .curated-workflow-collection-hidden {
        visibility: hidden;
    }

    .curated-workflow-collection-count {
        margin-left: 0.25rem;
        opacity: 0.7;
    }

    .curated-workflow-collections-more {
        position: absolute;
        top: 0;
        right: 0;
    }
}
</style>
