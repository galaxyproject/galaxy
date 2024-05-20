<script setup>
import { BNavItem, VBPopoverPlugin, VBTooltipPlugin } from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import Vue from "vue";

Vue.use(VBPopoverPlugin);
Vue.use(VBTooltipPlugin);

const emit = defineEmits(["click", "open-url"]);

/* props */
const props = defineProps({
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
        v-b-tooltip.hover.bottom
        v-b-popover.manual.bottom="{ id: id, content: popoverNote, html: true }"
        :href="withPrefix(url)"
        :target="target || '_parent'"
        :link-classes="linkClasses"
        :title="tooltip"
        @click="$emit('click')">
        <template v-if="icon">
            <!-- If this is an icon-based tab, inject tooltip directly for screen readers -->
            <span class="sr-only">{{ tooltip || id }}</span>
            <span :class="`fa ${icon}`" />
            <span v-if="toggle" class="nav-note fa fa-check" />
        </template>
        <template v-else>
            {{ title }}
        </template>
    </BNavItem>
</template>
