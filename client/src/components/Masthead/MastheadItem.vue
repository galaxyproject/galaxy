<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BNavItem, VBTooltipPlugin } from "bootstrap-vue";
import Vue from "vue";

import type { IconLike } from "@/components/icons/galaxyIcons";
import { withPrefix } from "@/utils/redirect";

Vue.use(VBTooltipPlugin);

/* props */
defineProps<{
    disabled?: boolean;
    id?: string;
    icon?: string | IconLike; // String for legacy CSS classes, IconLike for proper imports
    target?: string;
    title?: string;
    tooltip?: string;
    toggle?: boolean;
    url?: string;
}>();
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
            <FontAwesomeIcon v-if="typeof icon === 'object'" fixed-width :icon="icon" />
            <span v-else :class="`fa fa-fw ${icon}`" />
            <span v-if="toggle" class="nav-note fa fa-check" />
        </template>
        <template v-else>
            {{ title }}
        </template>
    </BNavItem>
</template>
