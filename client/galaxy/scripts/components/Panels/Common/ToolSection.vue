<template>
    <div>
        <div v-if="hasElements">
            <div class="toolSectionTitle">
                <a @click="toggleMenu" href="javascript:void(0)" role="button">
                    <span>
                        {{ this.name }}
                    </span>
                </a>
            </div>
            <transition name="slide">
                <div v-if="opened">
                    <template v-for="[key, el] in category.elems.entries()">
                        <div v-if="el.text" class="toolPanelLabel ml-2" :key="key">
                            <span>
                                {{ el.text }}
                            </span>
                        </div>
                        <tool v-else :tool="el" :key="key" :show-name="showName" @onClick="onClick" />
                    </template>
                </div>
            </transition>
        </div>
        <div v-else>
            <div v-if="category.text" class="toolPanelLabel">
                <span>
                    {{ category.text }}
                </span>
            </div>
            <tool v-else :tool="category" :no-section="true" :show-name="showName" @onClick="onClick" />
        </div>
    </div>
</template>

<script>
import Tool from "./Tool.vue";
import ariaAlert from "utils/ariaAlert";

export default {
    name: "ToolSection",
    components: {
        Tool
    },
    props: {
        category: {
            type: Object
        },
        isFiltered: {
            type: Boolean
        },
        showName: {
            type: Boolean,
            default: true
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
        onClick(e, tool) {
            this.$emit("onClick", e, tool);
        },
        toggleMenu(e) {
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
        isFiltered(newVal) {
            if (newVal) {
                this.opened = true;
            } else {
                this.opened = false;
            }
        }
    },
    mounted() {
        if (this.isFiltered) {
            this.opened = true;
        } else {
            this.opened = false;
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
