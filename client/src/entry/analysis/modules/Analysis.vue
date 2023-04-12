<script setup>
import HistoryIndex from "@/components/History/Index.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox";
import SidePanel from "@/components/Panels/SidePanel";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import CenterFrame from "./CenterFrame.vue";
import { useRoute, useRouter } from "vue-router/composables";
import { computed, ref, onMounted, onUnmounted } from "vue";
import { useUserStore } from "@/stores/userStore";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const showCenter = ref(false);

// computed
const showPanels = computed(() => {
    const panels = route.query.hide_panels;
    if (panels !== undefined) {
        return panels.toLowerCase() != "true";
    }
    return true;
});

const showActivityBar = computed(() => {
    return userStore.toggledActivityBar;
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
    <div v-if="showActivityBar" id="columns" class="d-flex">
        <ActivityBar v-if="showPanels" />
        <div id="center" class="overflow-auto p-3 w-100">
            <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
            <router-view v-show="!showCenter" :key="$route.fullPath" class="h-100" />
        </div>
        <FlexPanel v-if="showPanels" side="right">
            <HistoryIndex />
        </FlexPanel>
        <DragAndDropModal />
    </div>
    <div v-else id="columns">
        <SidePanel v-if="showPanels" side="left" :current-panel="ToolBox" :current-panel-properties="{}" />
        <div id="center" class="center-style">
            <div class="center-container">
                <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
                <div v-show="!showCenter" class="center-panel" style="display: block">
                    <router-view :key="$route.fullPath" class="h-100" />
                </div>
            </div>
        </div>
        <SidePanel v-if="showPanels" side="right" :current-panel="HistoryIndex" :current-panel-properties="{}" />
        <DragAndDropModal />
    </div>
</template>
