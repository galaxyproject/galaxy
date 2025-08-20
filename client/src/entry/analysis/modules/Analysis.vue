<script setup>
import { storeToRefs } from "pinia";
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { usePanels } from "@/composables/usePanels";
import { useUserStore } from "@/stores/userStore";

import CenterFrame from "./CenterFrame.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import HistoryIndex from "@/components/History/Index.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import TourRunner from "@/components/Tour/TourRunner.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";

const router = useRouter();
const route = useRoute();

const showCenter = ref(false);
const { showPanels } = usePanels();

const { historyPanelWidth } = storeToRefs(useUserStore());

/** Tour state - set manually */
const isTourRoute = ref(false);
/** Current tour ID - set manually */
const currentTourId = ref(null);

// Watch for route changes to detect tour routes
watch(
    () => route,
    (newRoute) => {
        if (newRoute.path.startsWith("/tours/") && newRoute.params.tourId) {
            isTourRoute.value = true;
            currentTourId.value = newRoute.params.tourId;
        }
    },
    { immediate: true, deep: true }
);

// methods
function endTour() {
    isTourRoute.value = false;
    currentTourId.value = null;
}

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
        <FlexPanel v-if="showPanels" side="right" :reactive-width.sync="historyPanelWidth">
            <HistoryIndex />
        </FlexPanel>
        <DragAndDropModal />
        <TourRunner v-if="isTourRoute" :key="currentTourId" :tour-id="currentTourId" @end-tour="endTour" />
    </div>
</template>
