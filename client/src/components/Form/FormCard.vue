<template>
    <div class="ui-portlet-section">
        <div :tabindex="collapsible ? 0 : -1" :class="portletHeaderClasses" @keydown="onKeyDown" @click="onCollapse">
            <div class="portlet-operations">
                <slot name="operations" />
                <GButton
                    v-if="collapsible"
                    tooltip
                    tooltip-placement="bottom"
                    title="Collapse/Expand"
                    color="blue"
                    transparent
                    size="small"
                    tabindex="-1">
                    <FontAwesomeIcon :icon="expanded ? faChevronUp : faChevronDown" class="fa-fw" />
                </GButton>
            </div>
            <span class="portlet-title">
                <span v-if="icon && typeof icon === 'string'" :class="['portlet-title-icon fa mr-1', icon]" />
                <FontAwesomeIcon v-else-if="icon && typeof icon === 'object'" :icon="icon" fixed-width class="mr-1" />
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

import GButton from "@/components/BaseComponents/GButton.vue";

export default {
    components: {
        FontAwesomeIcon,
        GButton,
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
            type: [String, Object], // String for legacy CSS classes, Object for icon objects
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
