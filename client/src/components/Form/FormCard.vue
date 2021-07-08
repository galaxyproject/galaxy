<template>
    <div class="ui-portlet-section">
        <div class="portlet-header">
            <div class="portlet-operations">
                <slot name="operations" />
                <b-button
                    v-if="collapsible"
                    role="button"
                    title="Collapse/Expand"
                    variant="link"
                    size="sm"
                    class="float-right py-0"
                    v-b-tooltip.hover.bottom
                    @click="onCollapse"
                >
                    <font-awesome-icon v-if="collapsed" icon="eye-slash" class="fa-fw" />
                    <font-awesome-icon v-else icon="eye" class="fa-fw" />
                </b-button>
            </div>
            <a class="portlet-title" @click="onCollapse" :href="href">
                <i :class="['portlet-title-icon fa mr-1', icon]" style="display: inline"></i>
                <span class="portlet-title-text">
                    <b itemprop="name">{{ title }}</b> <span itemprop="description">{{ description }}</span>
                </span>
            </a>
        </div>
        <div v-show="!collapsed" class="portlet-content">
            <slot name="body" />
        </div>
    </div>
</template>
<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye, faEyeSlash } from "@fortawesome/free-solid-svg-icons";

library.add(faEye);
library.add(faEyeSlash);

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
            type: String,
            default: "",
        },
        collapsible: {
            type: Boolean,
            default: false,
        },
        initialCollapse: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            collapsed: this.initialCollapse,
        };
    },
    computed: {
        href() {
            return this.collapsible ? "#" : null;
        },
    },
    methods: {
        onCollapse() {
            this.collapsed = this.collapsible && !this.collapsed;
        },
    },
};
</script>
