<template>
    <div v-if="isSection && hasElements" class="tool-panel-section">
        <div
            v-b-tooltip.topright.hover
            :class="['toolSectionTitle', `tool-menu-section-${sectionName}`]"
            :title="title"
            @mouseover="hover = true"
            @mouseleave="hover = false"
            @focus="hover = true"
            @blur="hover = false">
            <a class="title-link" href="javascript:void(0)" @click="toggleMenu()">
                <span class="name">
                    {{ name }}
                </span>
                <ToolPanelLinks :links="links" :show="hover" />
            </a>
        </div>
        <transition name="slide">
            <div v-if="opened">
                <template v-for="[key, el] in sortedElements">
                    <ToolPanelLabel v-if="category.text" :key="key" :definition="el" />
                    <tool
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
        <tool
            v-else
            :tool="category"
            :hide-name="hideName"
            :operation-title="operationTitle"
            :operation-icon="operationIcon"
            @onOperation="onOperation"
            @onClick="onClick" />
    </div>
</template>

<script>
import Tool from "./Tool";
import ToolPanelLabel from "./ToolPanelLabel";
import ariaAlert from "utils/ariaAlert";
import ToolPanelLinks from "./ToolPanelLinks";

import { useConfig } from "composables/config";

export default {
    name: "ToolSection",
    components: {
        Tool,
        ToolPanelLabel,
        ToolPanelLinks,
    },
    props: {
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
    },
    setup() {
        const { config, isLoaded } = useConfig();
        return {
            config,
            isLoaded,
        };
    },
    data() {
        return {
            opened: this.expanded || this.checkFilter(),
            hover: false,
        };
    },
    computed: {
        name() {
            return this.category.title || this.category.name;
        },
        isSection() {
            return this.category.elems !== undefined;
        },
        hasElements() {
            return this.category.elems && this.category.elems.length > 0;
        },
        title() {
            return this.category.description;
        },
        links() {
            return this.category.links || {};
        },
        sortedElements() {
            // If this.config.sortTools is true, sort the tools alphabetically
            // When administrators have manually inserted labels we respect
            // the order set and hope for the best from the integrated
            // panel.
            if (
                this.isLoaded &&
                this.config.toolbox_auto_sort === true &&
                this.sortItems === true &&
                !this.category.elems.some((el) => el.text !== undefined && el.text !== "")
            ) {
                const elements = [...this.category.elems];
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
                return Object.entries(this.category.elems);
            }
        },
    },
    watch: {
        queryFilter() {
            this.opened = this.checkFilter();
        },
        opened(newVal, oldVal) {
            if (newVal !== oldVal) {
                const currentState = newVal ? "opened" : "closed";
                ariaAlert(`${this.name} tools menu ${currentState}`);
            }
        },
    },
    created() {
        this.eventHub.$on("openToolSection", this.openToolSection);
    },
    beforeDestroy() {
        this.eventHub.$off("openToolSection", this.openToolSection);
    },
    methods: {
        openToolSection(sectionId) {
            if (this.isSection && sectionId == this.category?.id) {
                this.toggleMenu(true);
            }
        },
        checkFilter() {
            return !this.disableFilter && !!this.queryFilter;
        },
        onClick(tool, evt) {
            this.$emit("onClick", tool, evt);
        },
        onOperation(tool, evt) {
            this.$emit("onOperation", tool, evt);
        },
        toggleMenu(nextState = !this.opened) {
            this.opened = nextState;
        },
    },
};
</script>

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
</style>
