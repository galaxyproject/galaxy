<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import { eventHub } from "@/components/plugins/eventHub.js";
import { useConfig } from "@/composables/config";
import { type ToolSectionLabel, useToolStore } from "@/stores/toolStore";
import ariaAlert from "@/utils/ariaAlert";

import Tool from "./Tool.vue";
import ToolPanelLabel from "./ToolPanelLabel.vue";
import ToolPanelLinks from "./ToolPanelLinks.vue";

const emit = defineEmits<{
    (e: "onClick", tool: any, evt: Event): void;
    (e: "onOperation", tool: any, evt: Event): void;
}>();

const props = defineProps({
    category: {
        type: Object,
        required: true,
    },
    queryFilter: {
        type: String,
        default: "",
    },
    disableFilter: {
        type: Boolean,
    },
    hideName: {
        type: Boolean,
    },
    operationTitle: {
        type: String,
        default: "",
    },
    operationIcon: {
        type: String,
        default: "",
    },
    toolKey: {
        type: String,
        default: "",
    },
    sectionName: {
        type: String,
        default: "default",
    },
    expanded: {
        type: Boolean,
        default: false,
    },
    sortItems: {
        type: Boolean,
        default: true,
    },
});

const { config, isConfigLoaded } = useConfig();
const toolStore = useToolStore();

const elems = computed(() => {
    if (props.category.elems !== undefined && props.category.elems.length > 0) {
        return props.category.elems;
    }
    if (props.category.tools !== undefined && props.category.tools.length > 0) {
        return props.category.tools.map((toolId: string) => {
            const tool = toolStore.getToolForId(toolId);
            if (!tool && typeof toolId !== "string") {
                return toolId as ToolSectionLabel;
            } else {
                return tool;
            }
        });
    }
    return [];
});

const name = computed(() => props.category.title || props.category.name);
const isSection = computed(() => props.category.tools !== undefined || props.category.elems !== undefined);
const hasElements = computed(() => elems.value.length > 0);
const title = computed(() => props.category.description);
const links = computed(() => props.category.links || {});

const opened = ref(props.expanded || checkFilter());

const sortedElements = computed(() => {
    // If this.config.sortTools is true, sort the tools alphabetically
    // When administrators have manually inserted labels we respect
    // the order set and hope for the best from the integrated
    // panel.
    if (
        !checkFilter() &&
        isConfigLoaded.value &&
        config.value.toolbox_auto_sort === true &&
        props.sortItems === true &&
        !elems.value.some((el: ToolSectionLabel) => el.text !== undefined && el.text !== "")
    ) {
        const elements = [...elems.value];
        const sorted = elements.sort((a, b) => {
            const aNameLower = a.name.toLowerCase();
            const bNameLower = b.name.toLowerCase();
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
    }
);

watch(
    () => opened.value,
    (newVal: boolean, oldVal: boolean) => {
        if (newVal !== oldVal) {
            const currentState = newVal ? "opened" : "closed";
            ariaAlert(`${name.value} tools menu ${currentState}`);
        }
    }
);

onMounted(() => {
    eventHub.$on("openToolSection", openToolSection);
});

onUnmounted(() => {
    eventHub.$off("openToolSection", openToolSection);
});

function openToolSection(sectionId: string) {
    if (isSection.value && sectionId == props.category?.id) {
        toggleMenu(true);
    }
}
function checkFilter() {
    return !props.disableFilter && !!props.queryFilter;
}
function onClick(tool: any, evt: Event) {
    emit("onClick", tool, evt);
}
function onOperation(tool: any, evt: Event) {
    emit("onOperation", tool, evt);
}
function toggleMenu(nextState = !opened.value) {
    opened.value = nextState;
}
</script>

<template>
    <div v-if="isSection && hasElements" class="tool-panel-section">
        <div
            v-b-tooltip.topright.hover.noninteractive
            :class="['toolSectionTitle', `tool-menu-section-${sectionName}`]"
            :title="title">
            <a class="title-link" href="javascript:void(0)" @click="toggleMenu()">
                <span class="name">
                    {{ name }}
                </span>
                <ToolPanelLinks :links="links" />
            </a>
        </div>
        <transition name="slide">
            <div v-if="opened" data-description="opened tool panel section">
                <template v-for="[key, el] in sortedElements">
                    <ToolPanelLabel
                        v-if="category.text || el.model_class === 'ToolSectionLabel'"
                        :key="key"
                        :definition="el" />
                    <Tool
                        v-else
                        :key="key"
                        class="ml-2"
                        :tool="el"
                        :tool-key="toolKey"
                        :hide-name="hideName"
                        :operation-title="operationTitle"
                        :operation-icon="operationIcon"
                        @onOperation="onOperation"
                        @onClick="onClick" />
                </template>
            </div>
        </transition>
    </div>
    <div v-else>
        <ToolPanelLabel v-if="category.text" :definition="category" />
        <Tool
            v-else
            :tool="category"
            :hide-name="hideName"
            :operation-title="operationTitle"
            :operation-icon="operationIcon"
            @onOperation="onOperation"
            @onClick="onClick" />
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.tool-panel-label {
    background: darken($panel-bg-color, 5%);
    border-left: 0.25rem solid darken($panel-bg-color, 25%);
    font-size: $h5-font-size;
    font-weight: 600;
    padding-left: 0.75rem;
    padding-top: 0.25rem;
    padding-bottom: 0.25rem;
    text-transform: uppercase;
}

.tool-panel-section .tool-panel-label {
    /* labels within subsections */
    margin-left: 1.5rem;
    padding-top: 0.125rem;
    padding-bottom: 0.125rem;
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
