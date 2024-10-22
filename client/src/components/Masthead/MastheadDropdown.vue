<script setup>
import { BDropdownItem, BNavItemDropdown, VBTooltipPlugin } from "bootstrap-vue";
import Vue, { ref } from "vue";

import TextShort from "@/components/Common/TextShort.vue";

Vue.use(VBTooltipPlugin);

const dropdown = ref(null);

/* props */
defineProps({
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
    menu: {
        type: Array,
    },
});
</script>

<template>
    <BNavItemDropdown :id="id" ref="dropdown" v-b-tooltip.noninteractive.hover.bottom :title="tooltip" right>
        <template v-if="icon" v-slot:button-content>
            <span class="sr-only">{{ tooltip || id }}</span>
            <span class="fa fa-fw" :class="icon" />
            <TextShort :text="title" />
        </template>
        <template>
            <BDropdownItem v-for="(item, idx) in menu" :key="idx" role="menuitem" @click="item.handler">
                <span class="fa fa-fw" :class="item.icon" />
                <span>{{ item.title }}</span>
            </BDropdownItem>
        </template>
    </BNavItemDropdown>
</template>
