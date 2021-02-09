<template>
    <div v-if="isSection && hasElements" class="tool-panel-section">
        <div :class="['toolSectionTitle', `tool-menu-section-${sectionName}`]">
            <a @click="toggleMenu()" href="javascript:void(0)" role="button">
                <span class="name">
                    {{ this.name }}
                </span>
            </a>
        </div>
        <transition name="slide">
            <div v-if="opened">
                <template v-for="[key, el] in category.elems.entries()">
                    <div v-if="el.text" class="tool-panel-label" :key="key">
                        {{ el.text }}
                    </div>
                    <tool
                        v-else
                        class="ml-2"
                        :tool="el"
                        :key="key"
                        :tool-key="toolKey"
                        :hide-name="hideName"
                        :operation-title="operationTitle"
                        :operation-icon="operationIcon"
                        @onOperation="onOperation"
                        @onClick="onClick"
                    />
                </template>
            </div>
        </transition>
    </div>
    <div v-else>
        <div v-if="category.text" class="tool-panel-label">
            {{ category.text }}
        </div>
        <tool
            v-else
            :tool="category"
            :hide-name="hideName"
            :operation-title="operationTitle"
            :operation-icon="operationIcon"
            @onOperation="onOperation"
            @onClick="onClick"
        />
    </div>
</template>

<script>
import Tool from "./Tool";
import ariaAlert from "utils/ariaAlert";

export default {
    name: "ToolSection",
    components: {
        Tool,
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
        };
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
    created() {
        this.eventHub.$on("openToolSection", (sectionId) => {
            if (this.isSection && sectionId == this.category?.id) {
                this.toggleMenu(true);
            }
        });
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
