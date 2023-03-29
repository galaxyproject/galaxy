<script setup>
import { getGalaxyInstance } from "app";
import CenterFrame from "./CenterFrame.vue";
import { useUserStore } from "@/stores/userStore";
import HistoryIndex from "@/components/History/Index.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";
import { WindowManager } from "@/layout/window-manager";
import { useRoute, useRouter } from "vue-router/composables";
import { computed, ref, onMounted, onUnmounted } from "vue";

const route = useRoute();
const router = useRouter();
const showCenter = ref(false);
const userStore = useUserStore();

// computed
const showPanels = computed(() => {
    const panels = route.query.hide_panels;
    if (panels !== undefined) {
        return panels.toLowerCase() != "true";
    }
    return true;
});

// methods
function hideCenter() {
    showCenter.value = false;
}

function onLoad() {
    showCenter.value = true;
}

function sidebarIsActive(menuKey) {
    return userStore.toggledSideBar === menuKey;
}

function onToggleSidebar(toggle) {
    userStore.toggleSideBar(toggle);
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
        <div class="center-column overflow-auto p-3 w-100">
            <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
            <router-view v-show="!showCenter" :key="$route.fullPath" class="h-100" />
        </div>
        <HistoryIndex v-if="showPanels" class="right-column" />
        <DragAndDropModal />
    </div>
</template>

<style scoped>
@import "theme/blue.scss";

.right-column {
    min-width: 18rem;
    max-width: 18rem;
    width: 18rem;
}
</style>
