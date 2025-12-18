<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdownItem, BNavItemDropdown, VBTooltipPlugin } from "bootstrap-vue";
import Vue, { type PropType, ref } from "vue";

import type { IconLike } from "@/components/icons/galaxyIcons";

import TextShort from "@/components/Common/TextShort.vue";

Vue.use(VBTooltipPlugin);

const dropdown = ref(null);

interface MenuItem {
    title: string;
    icon?: IconLike;
    handler: () => void;
}

/* props */
defineProps({
    id: {
        type: String,
    },
    icon: {
        type: Object as PropType<IconLike>,
        required: false,
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
    menu: {
        type: Array as PropType<MenuItem[]>,
    },
});
</script>

<template>
    <BNavItemDropdown :id="id" ref="dropdown" v-b-tooltip.noninteractive.hover.bottom :title="tooltip ?? ''" right>
        <template v-if="icon" v-slot:button-content>
            <span class="sr-only">{{ tooltip || id }}</span>
            <FontAwesomeIcon fixed-width :icon="icon" />
            <TextShort :text="title ?? ''" />
        </template>
        <template>
            <BDropdownItem
                v-for="(item, idx) in menu"
                :key="idx"
                :data-description="`${id} ${item.title.toLowerCase()}`"
                role="menuitem"
                @click="item.handler">
                <FontAwesomeIcon v-if="item.icon" fixed-width :icon="item.icon" />
                <span>{{ item.title }}</span>
            </BDropdownItem>
        </template>
    </BNavItemDropdown>
</template>
