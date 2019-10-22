<template>
    <div>
        <div v-if="category.model_class.endsWith('ToolSection')" class="toolSectionWrapper">
            <div :id="category.name" class="toolSectionTitle">
                <a @click="toggleToolSectionMenu" href="javascript:void(0)" role="button">
                    <span>
                        {{ category.name }}
                    </span>
                </a>
            </div>
            <transition name="slide">
                <div v-if="opened">
                    <template v-for="tool in category.elems">
                        <tool v-if="tool.model_class.endsWith('Tool')" :tool="tool" :key="tool.id"></tool>
                        <div v-else-if="tool.model_class === 'ToolSectionLabel'" class="toolPanelLabel" :key="tool.id">
                            <span>
                                {{ tool.text }}
                            </span>
                        </div>
                    </template>
                </div>
            </transition>
        </div>
        <div v-else-if="category.model_class.endsWith('Tool')">
            <tool :tool="category" :no-section="true"></tool>
        </div>
        <div v-else-if="category.model_class.endsWith('ToolSectionLabel')" class="toolPanelLabel">
            <span>
                {{ category.text }}
            </span>
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
        }
    },
    methods: {
        toggleToolSectionMenu(e) {
            this.opened = !this.opened;
            const currentState = this.opened ? "opened" : "closed";
            ariaAlert(`${this.category.name} tools menu ${currentState}`);
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
