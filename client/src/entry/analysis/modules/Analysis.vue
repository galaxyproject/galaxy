<script setup>
import { getGalaxyInstance } from "app";
import CenterFrame from "./CenterFrame";
import { useUserStore } from "@/stores/userStore";
import HistoryIndex from "@/components/History/Index";
import { WindowManager } from "@/layout/window-manager";
import ToolBox from "@/components/Panels/ProviderAwareToolBox";
import { UploadButton } from "@/components/Upload";
import { useRoute, useRouter } from "vue-router/composables";
import { computed, ref, onMounted, onUnmounted } from "vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal";

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
const toolBoxProperties = computed(() => {
    const Galaxy = getGalaxyInstance();
    return {
        storedWorkflowMenuEntries: Galaxy.config.stored_workflow_menu_entries,
    };
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
        <b-nav v-if="showPanels" vertical class="side-bar pt-1">
            <b-nav-item
                id="tool-search"
                v-b-tooltip.hover.right
                class="my-1"
                :class="{ 'active-sidebar': sidebarIsActive('search') }"
                :title="'Search Tools and Workflows' | l"
                @click="onToggleSidebar('search')">
                <template>
                    <span class="fa fa-wrench nav-icon" />
                    <span v-if="sidebarIsActive('search')" class="fa fa-caret-right nav-icon-active" />
                </template>
            </b-nav-item>
            <upload-button />
        </b-nav>
        <transition-group name="panels">
            <div v-if="showPanels" v-show="sidebarIsActive('search')" key="search">
                <ToolBox v-bind="toolBoxProperties" class="left-column" />
            </div>
        </transition-group>
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

.nav-item {
    cursor: pointer;
    text-decoration: none;
    list-style-type: none;
}

.left-column {
    min-width: 15.2rem;
    max-width: 15.2rem;
    width: 15.2rem;
}

.right-column {
    min-width: 18rem;
    max-width: 18rem;
    width: 18rem;
}

.side-bar {
    z-index: 100;
    width: 2.8rem;
    min-width: 2.8rem;
    max-width: 2.8rem;
    background: $panel-bg-color;
}

.active-sidebar {
    border-radius: 10px;
    background: $gray-300;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}

.nav-icon {
    height: 2rem;
    display: flex;
    align-items: center;
    align-content: center;
}

.nav-icon-active {
    top: 40%;
    left: 100%;
    position: absolute;
}

.panels-enter-active,
.panels-leave-active {
    transition: all 0.3s;
}

.panels-enter,
.panels-leave-to {
    transform: translateX(-100%);
}
</style>
