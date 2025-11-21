<script setup>
import { storeToRefs } from "pinia";
import { onMounted, onUnmounted, ref } from "vue";

import { usePanels } from "@/composables/usePanels";
import { useUserStore } from "@/stores/userStore";
import { eventBus } from "@/utils/eventBus";

import CenterFrame from "./CenterFrame.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import HistoryIndex from "@/components/History/Index.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";

const showCenter = ref(false);
const { showPanels } = usePanels();

const historyPanel = ref(null);

const { historyPanelWidth } = storeToRefs(useUserStore());

// methods
function hideCenter() {
    showCenter.value = false;
}

function onShow(showPanel) {
    if (historyPanel.value) {
        historyPanel.value.show = showPanel;
    }
}

function onLoad() {
    showCenter.value = true;
}

// life cycle
onMounted(() => {
    // Using a custom event here which, in contrast to watching $route,
    // always fires when a route is pushed instead of validating it first.
    eventBus.on("router-push", hideCenter);
});

onUnmounted(() => {
    eventBus.off("router-push", hideCenter);
});
</script>

<template>
    <div id="columns" class="d-flex">
        <ActivityBar v-if="showPanels" />
        <div id="center" class="overflow-auto p-3 w-100">
            <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
            <div v-show="!showCenter" class="h-100">
                <router-view :key="$route.fullPath" class="h-100" />
            </div>
        </div>
        <FlexPanel v-if="showPanels" ref="historyPanel" v-model:reactive-width="historyPanelWidth" side="right">
            <HistoryIndex @show="onShow" />
        </FlexPanel>
        <DragAndDropModal />
    </div>
</template>
