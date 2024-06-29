<script setup>
import { BNavItem, VBTooltipPlugin } from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import Vue from "vue";

Vue.use(VBTooltipPlugin);

/* props */
defineProps({
    disabled: {
        type: Boolean,
    },
    id: {
        type: String,
    },
    icon: {
        type: String,
    },
    target: {
        type: String,
    },
    title: {
        type: String,
    },
    tooltip: {
        type: String,
    },
    toggle: {
        type: Boolean,
        default: false,
    },
    url: {
        type: String,
    },
});
</script>

<template>
    <BNavItem
        :id="id"
        v-b-tooltip.noninteractive.hover.bottom
        :href="withPrefix(url)"
        :target="target || '_parent'"
        :link-classes="{ 'nav-icon': !!icon, toggle: toggle }"
        :title="tooltip"
        @click.prevent="$emit('click')">
        <template v-if="icon">
            <!-- If this is an icon-based tab, inject tooltip directly for screen readers -->
            <span class="sr-only">{{ tooltip || id }}</span>
            <span :class="`fa fa-fw ${icon}`" />
            <span v-if="toggle" class="nav-note fa fa-check" />
        </template>
        <template v-else>
            {{ title }}
        </template>
    </BNavItem>
</template>
