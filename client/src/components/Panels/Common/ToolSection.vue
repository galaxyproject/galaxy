<script setup lang="ts">
import { faFilter } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useEventBus } from "@vueuse/core";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { isTool, isToolSection, isToolSectionLabel } from "@/api/tools";
import { useConfig } from "@/composables/config";
import { type Tool as ToolType, type ToolPanelItem, useToolStore } from "@/stores/toolStore";
import ariaAlert from "@/utils/ariaAlert";

import { PANEL_LABEL_IDS } from "../panelViews";

import Tool from "./Tool.vue";
import ToolPanelLabel from "./ToolPanelLabel.vue";
import ToolPanelLinks from "./ToolPanelLinks.vue";

const emit = defineEmits<{
    (e: "onClick", tool: ToolType, evt: Event): void;
    (e: "onFilter", filter: string): void;
    (e: "onLabelToggle", labelId: string): void;
}>();

const eventBus = useEventBus<string>("open-tool-section");

interface Props {
    category: ToolPanelItem;
    queryFilter?: string;
    disableFilter?: boolean;
    hideName?: boolean;
    expanded?: boolean;
    sortItems?: boolean;
    hasFilterButton?: boolean;
    searchActive?: boolean;
    showFavoriteButton?: boolean;
    collapsedLabels?: {
        [PANEL_LABEL_IDS.FAVORITES_LABEL]: boolean;
        [PANEL_LABEL_IDS.FAVORITES_RESULTS_LABEL]: boolean;
        [PANEL_LABEL_IDS.RECENT_TOOLS_LABEL]: boolean;
    } | null;
}

const props = withDefaults(defineProps<Props>(), {
    queryFilter: "",
    disableFilter: false,
    hideName: false,
    expanded: false,
    sortItems: true,
    hasFilterButton: false,
    searchActive: false,
    showFavoriteButton: false,
    collapsedLabels: null,
});

const { config, isConfigLoaded } = useConfig();
const toolStore = useToolStore();

/**
 * We can have sections of 2 types:
 * 1. Sections with `elems` property, which is an array of tools and sections.
 * 2. Sections with `tools` property, which is an array of tool IDs (strings) and section labels.
 *    In this case, we need to resolve the tool IDs to get the actual tools.
 */
const elems = computed(() => {
    if (isToolSection(props.category)) {
        if (props.category.elems !== undefined && props.category.elems.length > 0) {
            // This section has `elems`, we can return it as is.
            return props.category.elems;
        }
        if (props.category.tools !== undefined && props.category.tools.length > 0) {
            return props.category.tools
                .map((toolOrLabel) => {
                    if (typeof toolOrLabel === "string") {
                        // This is a tool ID, we need to resolve it to get the actual `Tool`.
                        return toolStore.getToolForId(toolOrLabel) || null;
                    } else {
                        // This is a `ToolSectionLabel`, we can return it as is.
                        return toolOrLabel;
                    }
                })
                .filter((el) => el !== null);
        }
    }
    return [];
});

const opened = ref(props.expanded || checkFilter());

const sortedElements = computed<Array<[string, ToolPanelItem]>>(() => {
    // If this.config.sortTools is true, sort the tools alphabetically
    // When administrators have manually inserted labels we respect
    // the order set and hope for the best from the integrated
    // panel.
    if (
        !checkFilter() &&
        isConfigLoaded.value &&
        config.value.toolbox_auto_sort === true &&
        props.sortItems === true &&
        !elems.value.some((el) => isToolSectionLabel(el) && el.text !== "")
    ) {
        const elements = [...elems.value];
        const sorted = elements.sort((a, b) => {
            const aNameLower = "name" in a ? a.name.toLowerCase() : "";
            const bNameLower = "name" in b ? b.name.toLowerCase() : "";
            if (aNameLower > bNameLower) {
                return 1;
            } else if (aNameLower < bNameLower) {
                return -1;
            } else {
                return 0;
            }
        });
        return Object.entries(sorted);
    } else {
        return Object.entries(elems.value);
    }
});

watch(
    () => props.queryFilter,
    () => {
        opened.value = checkFilter();
    },
);

watch(
    () => opened.value,
    (newVal: boolean, oldVal: boolean) => {
        if (newVal !== oldVal && isToolSection(props.category)) {
            const currentState = newVal ? "opened" : "closed";
            ariaAlert(`${props.category.name} tools menu ${currentState}`);
        }
    },
);

onMounted(() => {
    eventBus.on(openToolSection);
});

onUnmounted(() => {
    eventBus.off(openToolSection);
});

function openToolSection(sectionId: string) {
    if (isToolSection(props.category) && sectionId == props.category?.id) {
        toggleMenu(true);
    }
}
function checkFilter() {
    return !props.disableFilter && !!props.queryFilter;
}
function onClick(tool: ToolType, evt: Event) {
    emit("onClick", tool, evt);
}
function onLabelToggle(labelId: string) {
    emit("onLabelToggle", labelId);
}
function toggleMenu(nextState = !opened.value) {
    opened.value = nextState;
}
function getCollapsedState(id: string): boolean | undefined {
    const validStateLabels = [
        PANEL_LABEL_IDS.FAVORITES_LABEL,
        PANEL_LABEL_IDS.FAVORITES_RESULTS_LABEL,
        PANEL_LABEL_IDS.RECENT_TOOLS_LABEL,
    ] as const;
    if (validStateLabels.includes(id as (typeof validStateLabels)[number])) {
        return props.collapsedLabels ? props.collapsedLabels[id as (typeof validStateLabels)[number]] : undefined;
    }
    return undefined;
}
</script>

<template>
    <div v-if="isToolSection(props.category) && elems.length > 0" class="tool-panel-section">
        <div
            v-b-tooltip.topright.hover.noninteractive
            class="toolSectionTitle tool-panel-divider"
            :title="props.category.description || undefined">
            <a
                class="title-link tool-panel-divider-link"
                href="javascript:void(0)"
                role="button"
                :aria-expanded="opened"
                @click="toggleMenu()">
                <span class="tool-panel-divider-text">
                    <span class="name">
                        {{ props.category.title || props.category.name }}
                    </span>
                    <ToolPanelLinks v-if="props.category.links" :links="props.category.links" />
                    <button
                        v-if="props.hasFilterButton"
                        v-b-tooltip.hover.noninteractive.bottom
                        title="Show full section"
                        class="inline-icon-button"
                        @click.stop="emit('onFilter', `section:${props.category.name}`)">
                        <FontAwesomeIcon :icon="faFilter" />
                    </button>
                </span>
            </a>
        </div>
        <transition name="slide">
            <div v-if="opened" data-description="opened tool panel section">
                <template v-for="[key, el] in sortedElements">
                    <ToolPanelLabel
                        v-if="isToolSectionLabel(el)"
                        :key="`label-${key}`"
                        :definition="el"
                        :collapsed="getCollapsedState(el.id)"
                        @toggle="onLabelToggle" />
                    <Tool
                        v-else-if="isTool(el)"
                        :key="`tool-${key}`"
                        class="ml-2"
                        :tool="el"
                        :hide-name="hideName"
                        :show-favorite-button="props.showFavoriteButton || searchActive"
                        @onClick="onClick" />
                </template>
            </div>
        </transition>
    </div>
    <ToolPanelLabel
        v-else-if="isToolSectionLabel(props.category)"
        :definition="props.category"
        :collapsed="getCollapsedState(props.category.id)"
        @toggle="onLabelToggle" />
    <Tool
        v-else-if="isTool(props.category)"
        :tool="props.category"
        :hide-name="hideName"
        :show-favorite-button="props.showFavoriteButton || searchActive"
        @onClick="onClick" />
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.inline-icon-button {
    font-size: 75%;
    padding: 0em 0.5em;
}

.tool-panel-label:not(.tool-panel-divider) {
    border-left: 0.25rem solid darken($panel-bg-color, 25%);
    font-size: $h5-font-size;
    font-weight: 600;
    padding-left: 0.75rem;
    padding-top: 0.25rem;
    padding-bottom: 0.25rem;
    text-transform: uppercase;
}

.tool-panel-section .tool-panel-label:not(.tool-panel-divider) {
    /* labels within subsections */
    margin-left: 1.5rem;
    padding-top: 0.125rem;
    padding-bottom: 0.125rem;
}

.tool-panel-section .tool-panel-label.tool-panel-divider {
    margin-left: 1.5rem;
}

.slide-enter-active {
    -moz-transition-duration: 0.2s;
    -webkit-transition-duration: 0.2s;
    -o-transition-duration: 0.2s;
    transition-duration: 0.2s;
    -moz-transition-timing-function: ease-in;
    -webkit-transition-timing-function: ease-in;
    -o-transition-timing-function: ease-in;
    transition-timing-function: ease-in;
}

.slide-leave-active {
    -moz-transition-duration: 0.2s;
    -webkit-transition-duration: 0.2s;
    -o-transition-duration: 0.2s;
    transition-duration: 0.2s;
    -moz-transition-timing-function: cubic-bezier(0, 1, 0.5, 1);
    -webkit-transition-timing-function: cubic-bezier(0, 1, 0.5, 1);
    -o-transition-timing-function: cubic-bezier(0, 1, 0.5, 1);
    transition-timing-function: cubic-bezier(0, 1, 0.5, 1);
}

.slide-enter-to,
.slide-leave {
    max-height: 100px;
    overflow: hidden;
}

.slide-enter,
.slide-leave-to {
    overflow: hidden;
    max-height: 0;
}

.title-link {
    &:deep(.tool-panel-links) {
        display: none;
    }

    &:hover,
    &:focus,
    &:focus-within {
        &:deep(.tool-panel-links) {
            display: inline;
        }
    }
}
</style>
