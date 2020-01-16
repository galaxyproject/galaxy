<template>
    <div>
        <div v-if="hasElements">
            <div :class="['toolSectionTitle', `tool-menu-section-${sectionName}`]">
                <a @click="toggleMenu" href="javascript:void(0)" role="button">
                    <span class="name">
                        {{ this.name }}
                    </span>
                </a>
            </div>
            <transition name="slide">
                <div v-if="opened">
                    <template v-for="[key, el] in category.elems.entries()">
                        <span v-if="el.text" class="label toolPanelLabel ml-2" :key="key">
                            {{ el.text }}
                        </span>
                        <tool
                            v-else
                            class="ml-2"
                            :tool="el"
                            :key="key"
                            :toolKey="toolKey"
                            :hideName="hideName"
                            :operationTitle="operationTitle"
                            :operationIcon="operationIcon"
                            @onOperation="onOperation"
                            @onClick="onClick"
                        />
                    </template>
                </div>
            </transition>
        </div>
        <div v-else>
            <span v-if="category.text" class="label toolPanelLabel">
                {{ category.text }}
            </span>
            <tool
                v-else
                :tool="category"
                :hideName="hideName"
                :operationTitle="operationTitle"
                :operationIcon="operationIcon"
                @onOperation="onOperation"
                @onClick="onClick"
            />
        </div>
    </div>
</template>

<script>
import Tool from "./Tool";
import ariaAlert from "utils/ariaAlert";

export default {
    name: "ToolSection",
    components: {
        Tool
    },
    props: {
        category: {
            type: Object,
            required: true
        },
        isFiltered: {
            type: Boolean
        },
        isFilterable: {
            type: Boolean
        },
        hideName: {
            type: Boolean
        },
        operationTitle: {
            type: String
        },
        operationIcon: {
            type: String
        },
        toolKey: {
            type: String
        },
        sectionName: {
            type: String,
            default: "default"
        }
    },
    computed: {
        name() {
            return this.category.title || this.category.name;
        },
        hasElements() {
            return this.category.elems && this.category.elems.length > 0;
        }
    },
    methods: {
        onClick(tool, evt) {
            this.$emit("onClick", tool, evt);
        },
        onOperation(tool, evt) {
            this.$emit("onOperation", tool, evt);
        },
        toggleMenu() {
            this.opened = !this.opened;
            const currentState = this.opened ? "opened" : "closed";
            ariaAlert(`${this.name} tools menu ${currentState}`);
        }
    },
    data() {
        return {
            opened: false
        };
    },
    watch: {
        isFiltered(state) {
            this.opened = this.isFilterable && !!state;
        }
    }
};
</script>

<style scoped>
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
