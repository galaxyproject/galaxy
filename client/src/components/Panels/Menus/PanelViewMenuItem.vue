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
    if (props.currentPanelView === props.panelView.id) {
        return faCheck;
    } else {
        return types_to_icons[viewType] || faEye;
    }
});
</script>

<template>
    <BDropdownItem
        class="ml-1"
        :title="props.panelView.description"
        :data-panel-id="panelView.id"
        :active="props.currentPanelView === props.panelView.id"
        @click="emit('onSelect', props.panelView)">
        <FontAwesomeIcon :icon="icon" data-description="panel view item icon" fixed-width />
        <span v-localize>{{ props.panelView.name }}</span>
    </BDropdownItem>
</template>
