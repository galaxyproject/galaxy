<template>
    <div class="ui-portlet-section">
        <div class="portlet-header">
            <div class="portlet-operations">
                <slot name="operations" />
                <b-button
                    v-if="collapsible"
                    v-b-tooltip.hover.bottom
                    role="button"
                    title="Collapse/Expand"
                    variant="link"
                    size="sm"
                    class="float-right"
                    @click="onCollapse">
                    <font-awesome-icon v-if="expanded" icon="eye-slash" class="fa-fw" />
                    <font-awesome-icon v-else icon="eye" class="fa-fw" />
                </b-button>
            </div>
            <b-link v-if="collapsible" class="portlet-title" href="#" @click="onCollapse">
                <FontAwesomeIcon v-if="icon" :icon="icon" class="portlet-title-icon mr-1" />
                <b class="portlet-title-text" itemprop="name">{{ title }}</b>
                <span class="portlet-title-description" itemprop="description">{{ description }}</span>
            </b-link>
            <span v-else class="portlet-title">
                <FontAwesomeIcon v-if="icon" :icon="icon" class="portlet-title-icon mr-1" />
                <b class="portlet-title-text" itemprop="name">{{ title }}</b>
                <span class="portlet-title-description" itemprop="description">{{ description }}</span>
            </span>
        </div>
        <div v-show="expanded" class="portlet-content">
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
        return {};
    },
    methods: {
        onCollapse() {
            if (this.collapsible) {
                this.$emit("update:expanded", !this.expanded);
            }
        },
    },
};
</script>
