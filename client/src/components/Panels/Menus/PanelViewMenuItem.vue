<script setup lang="ts">
import { faCheck, faEye } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdownItem } from "bootstrap-vue";
import { computed } from "vue";

import type { Panel } from "@/stores/toolStore";

import { MY_PANEL_VIEW_ID, MY_PANEL_VIEW_NAME } from "../panelViews";
import { types_to_icons } from "../utilities";

const props = defineProps<{
    currentPanelView: string;
    panelView: Panel;
}>();

const emit = defineEmits<{
    (e: "onSelect", panelView: Panel): void;
}>();

const isFavoritesView = computed(() => props.panelView.view_type === "favorites");
const isMyToolsView = computed(() => props.panelView.id === MY_PANEL_VIEW_ID);
const showPanelIcon = computed(() => !isMyToolsView.value || props.currentPanelView === props.panelView.id);
const panelViewName = computed(() =>
    props.panelView.id === MY_PANEL_VIEW_ID ? MY_PANEL_VIEW_NAME : props.panelView.name,
);

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
        <FontAwesomeIcon
            v-if="showPanelIcon && !isFavoritesView"
            :icon="icon"
            class="mr-1"
            data-description="panel view item icon"
            fixed-width />
        <span v-localize>{{ panelViewName }}</span>
        <FontAwesomeIcon
            v-if="showPanelIcon && isFavoritesView"
            :icon="icon"
            class="ml-1"
            data-description="panel view item icon"
            fixed-width />
    </BDropdownItem>
</template>
