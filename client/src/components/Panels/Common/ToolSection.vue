<template>
    <div v-if="isSection && hasElements" class="tool-panel-section">
        <div
            v-b-tooltip.topright.hover
            :class="['toolSectionTitle', `tool-menu-section-${sectionName}`]"
            :title="title"
            @mouseover="hover = true"
            @mouseleave="hover = false">
            <a class="title-link" href="javascript:void(0)" @click="toggleMenu()">
                <span class="name">
                    {{ name }}
                </span>
                <ToolPanelLinks :links="links" :show="hover" />
            </a>
        </div>
        <transition name="slide">
            <div v-if="opened">
                <template v-for="[key, el] in category.elems.entries()">
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
        this.eventHub.$on("openToolSection", (sectionId) => {
            if (this.isSection && sectionId == this.category?.id) {
                this.toggleMenu(true);
            }
        });
    },
    methods: {
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
