<script setup>
import { storeToRefs } from "pinia";
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { usePanels } from "@/composables/usePanels";
import { useHelpModeStore } from "@/stores/helpmode/helpModeStore";

import CenterFrame from "./CenterFrame.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import HistoryIndex from "@/components/History/Index.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import HelpModeText from "@/components/Panels/HelpModeText.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";

const router = useRouter();
const showCenter = ref(false);
const { showPanels } = usePanels();
const { status: helpModeStatus } = storeToRefs(useHelpModeStore());

// methods
function hideCenter() {
    showCenter.value = false;
}

function onLoad() {
    showCenter.value = true;
}

// life cycle
onMounted(() => {
    // Using a custom event here which, in contrast to watching $route,
    // always fires when a route is pushed instead of validating it first.
    router.app.$on("router-push", hideCenter);
});

onUnmounted(() => {
    router.app.$off("router-push", hideCenter);
});
</script>

<template>
    <div id="columns" class="d-flex">
        <ActivityBar />
        <div id="center" class="overflow-auto p-3 w-100">
            <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
            <router-view v-show="!showCenter" :key="$route.fullPath" class="h-100" />
        </div>
        <FlexPanel v-if="showPanels" side="right">
            <HistoryIndex />
        </FlexPanel>
        <DragAndDropModal />
        <HelpModeText v-if="helpModeStatus" />
    </div>
</template>
