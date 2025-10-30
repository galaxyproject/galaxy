<template>
    <div class="ui-portlet-section">
        <div :tabindex="collapsible ? 0 : -1" :class="portletHeaderClasses" @keydown="onKeyDown" @click="onCollapse">
            <div class="portlet-operations">
                <slot name="operations" />
                <span
                    v-if="collapsible"
                    v-b-tooltip.hover.bottom
                    title="Collapse/Expand"
                    variant="link"
                    size="sm"
                    class="float-right">
                    <FontAwesomeIcon v-if="expanded" :icon="faChevronUp" class="fa-fw" />
                    <FontAwesomeIcon v-else :icon="faChevronDown" class="fa-fw" />
                </span>
            </div>
            <span class="portlet-title">
                <span v-if="icon" :class="['portlet-title-icon fa mr-1', icon]" />
                <b class="portlet-title-text" itemprop="name">{{ title }}</b>
                <slot name="title" />
                <span class="portlet-title-description" itemprop="description">{{ description }}</span>
            </span>
        </div>
        <div v-show="expanded" class="portlet-content">
            <slot name="body" />
        </div>
    </div>
</template>

<script>
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { IconDefinition } from "font-awesome-6";

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            default: null,
        },
        icon: {
            type: IconDefinition,
            default: null,
        },
        collapsible: {
            type: Boolean,
            default: false,
        },
        expanded: {
            type: Boolean,
            default: true,
        },
    },
    data() {
        return {
            faChevronUp,
            faChevronDown,
        };
    },
    computed: {
        portletHeaderClasses() {
            return {
                "portlet-header": true,
                "cursor-pointer": this.collapsible,
            };
        },
    },
    methods: {
        onKeyDown(event) {
            if (event.key === "Enter" || event.key === " ") {
                this.onCollapse();
            }
        },
        onCollapse() {
            if (this.collapsible) {
                this.$emit("update:expanded", !this.expanded);
            }
        },
    },
};
</script>
