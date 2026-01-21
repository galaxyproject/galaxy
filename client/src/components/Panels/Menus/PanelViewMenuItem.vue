<script setup lang="ts">
import { faCheck, faEye } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdownItem } from "bootstrap-vue";
import { computed } from "vue";

import type { Panel } from "@/stores/toolStore";

import { types_to_icons } from "../utilities";

const props = defineProps<{
    currentPanelView: string;
    panelView: Panel;
}>();

const emit = defineEmits<{
    (e: "onSelect", panelView: Panel): void;
}>();

const icon = computed(() => {
    const viewType = props.panelView.view_type;
    return types_to_icons[viewType] || faEye;
});

const isSelected = computed(() => props.currentPanelView === props.panelView.id);
</script>

<template>
    <BDropdownItem
        class="ml-1"
        :title="props.panelView.description"
        :data-panel-id="panelView.id"
        :active="isSelected"
        @click="emit('onSelect', props.panelView)">
        <FontAwesomeIcon :icon="icon" class="mr-1" fixed-width />
        <span v-localize>{{ panelView.name }}</span>
        <FontAwesomeIcon v-if="isSelected" :icon="faCheck" class="ml-1" fixed-width />
    </BDropdownItem>
</template>
