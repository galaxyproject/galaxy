<template>
    <div class="ui-portlet-section">
        <div class="portlet-header">
            <div class="portlet-operations">
                <slot name="operations" />
            </div>
            <div class="portlet-title">
                <i :class="['portlet-title-icon fa mr-1', icon]" style="display: inline"></i>
                <span class="portlet-title-text">
                    <b itemprop="name">{{ title }}</b> <span itemprop="description">{{ description }}</span>
                </span>
            </div>
        </div>
        <div class="portlet-content">
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
            required: false,
        },
        icon: {
            type: String,
            default: "fa-wrench",
        },
    },
};
</script>
