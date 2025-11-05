<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BNavItem, VBTooltipPlugin } from "bootstrap-vue";
import Vue, { type PropType } from "vue";

import type { IconLike } from "@/components/icons/galaxyIcons";
import { withPrefix } from "@/utils/redirect";

Vue.use(VBTooltipPlugin);

/* props */
defineProps({
    disabled: Boolean,
    id: String,
    icon: [Object, String] as PropType<IconLike | string>,
    target: String,
    title: String,
    tooltip: String,
    toggle: Boolean,
    url: String,
});
</script>

<template>
    <BNavItem
        :id="id"
        v-b-tooltip.noninteractive.hover.bottom
        :href="url ? withPrefix(url) : undefined"
        :target="target || '_parent'"
        :link-classes="{ 'nav-icon': !!icon, toggle: toggle }"
        :title="tooltip"
        @click.prevent="$emit('click')">
        <template v-if="icon">
            <!-- If this is an icon-based tab, inject tooltip directly for screen readers -->
            <span class="sr-only">{{ tooltip || id }}</span>
            <!-- Support both FontAwesome icon objects and legacy string icon names -->
            <FontAwesomeIcon v-if="typeof icon === 'object'" fixed-width :icon="icon" />
            <span v-else class="fa" :class="icon" />
            <span v-if="toggle" class="nav-note fa fa-check" />
        </template>
        <template v-else>
            {{ title }}
        </template>
    </BNavItem>
</template>
