<script setup>
import { computed, ref, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router/composables";
import { useUserStore } from "@/stores/userStore";
import HistoryIndex from "@/components/History/Index.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import CenterFrame from "./CenterFrame.vue";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const showCenter = ref(false);

// computed
const showPanels = computed(() => {
    const panels = route.query.hide_panels;
    if (panels !== undefined && panels !== null && typeof panels === "string") {
        return panels.toLowerCase() != "true";
    }
    return true;
});

const showActivityBar = computed(() => {
    return userStore.showActivityBar;
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
        <ActivityBar v-if="showPanels && showActivityBar" />
        <FlexPanel v-if="showPanels && !showActivityBar" side="left">
            <ToolBox />
        </FlexPanel>
        <div id="center" class="overflow-auto p-3 w-100">
            <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
            <router-view v-show="!showCenter" :key="$route.fullPath" class="h-100" />
        </div>
        <FlexPanel v-if="showPanels" side="right">
            <HistoryIndex />
        </FlexPanel>
        <DragAndDropModal />
    </div>
</template>
