<script setup>
import { getGalaxyInstance } from "app";
import { useUserStore } from "@/stores/userStore";
import { WindowManager } from "@/layout/window-manager";
import { useRoute, useRouter } from "vue-router/composables";
import { computed, ref } from "vue";
import UploadButton from "./Items/UploadButton.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox.vue";

const route = useRoute();
const router = useRouter();
const showCenter = ref(false);
const userStore = useUserStore();

const toolBoxProperties = computed(() => {
    const Galaxy = getGalaxyInstance();
    return {
        storedWorkflowMenuEntries: Galaxy.config.stored_workflow_menu_entries,
    };
});

function sidebarIsActive(menuKey) {
    return userStore.toggledSideBar === menuKey;
}

function onToggleSidebar(toggle) {
    userStore.toggleSideBar(toggle);
}
</script>
<template>
    <div class="d-flex">
        <b-nav vertical class="side-bar flex-nowrap p-1">
            <b-nav-item
                id="tool-search"
                :class="{ 'nav-item-active': sidebarIsActive('search') }"
                :title="'Search Tools and Workflows' | l"
                @click="onToggleSidebar('search')">
                <template>
                    <span class="nav-icon fa fa-wrench" />
                </template>
            </b-nav-item>
            <upload-button />
        </b-nav>
        <div v-show="sidebarIsActive('search')" key="search">
            <ToolBox class="left-column" v-bind="toolBoxProperties" />
        </div>
    </div>
</template>

<style scoped>
@import "theme/blue.scss";

.left-column {
    min-width: 15rem;
    max-width: 15rem;
    width: 15rem;
}

.side-bar {
    background: $panel-bg-color;
    overflow-y: auto;
}

.side-bar::-webkit-scrollbar {
    display: none;
}

.nav-item-active {
    border-radius: 0.5rem;
    background: $gray-300;
}

.nav-icon {
    height: 2rem;
    display: flex;
    align-items: center;
    align-content: center;
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
