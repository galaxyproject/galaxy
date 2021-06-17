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
                    v-b-tooltip.hover
                    @click="onCollapse"
                >
                    <span v-if="collapsed" class="fa fa-eye" />
                    <span v-else class="fa fa-eye-slash" />
                </b-button>
            </div>
            <a class="portlet-title" @click="onCollapse" :href="href">
                <i :class="['portlet-title-icon fa mr-1', icon]" style="display: inline"></i>
                <span class="portlet-title-text">
                    <b itemprop="name">{{ title }}</b> <span itemprop="description">{{ description }}</span>
                </span>
            </a>
        </div>
        <div v-if="!collapsed" class="portlet-content">
            <slot name="body" />
        </div>
    </div>
</template>
<script>
export default {
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
    },
    data() {
        return {
            collapsed: this.collapsible,
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
