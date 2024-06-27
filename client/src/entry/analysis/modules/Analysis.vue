<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { usePanels } from "@/composables/usePanels";
import { useConfig } from "@/composables/config";

import CenterFrame from "./CenterFrame.vue";
import WorkflowLanding from "./WorkflowLanding.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import HistoryIndex from "@/components/History/Index.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";

const router = useRouter();
const showCenter = ref(false);
const { showPanels } = usePanels();
const { config, isConfigLoaded } = useConfig();

const showHistoryPanel = computed(() => {
    return showPanels.value && config.value && config.value.client_mode == "full";
});

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
        <ActivityBar v-if="showPanels" />
        <div id="center" class="overflow-auto p-3 w-100">
            <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
            <div v-show="!showCenter" class="h-100">
                <router-view :key="$route.fullPath" class="h-100" />
            </div>
        </div>
        <FlexPanel v-if="showHistoryPanel" side="right">
            <HistoryIndex />
        </FlexPanel>
        <DragAndDropModal />
    </div>
</template>
