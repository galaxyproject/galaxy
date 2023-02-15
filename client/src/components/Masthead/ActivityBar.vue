<script setup>
import { getGalaxyInstance } from "app";
import { useUserStore } from "@/stores/userStore";
import { WindowManager } from "@/layout/window-manager";
import { UploadButton } from "@/components/Upload";
import { useRoute, useRouter } from "vue-router/composables";
import { computed, ref } from "vue";
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
        <b-nav vertical class="side-bar pt-1">
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
        <div v-show="!sidebarIsActive('search')" key="search">
            <ToolBox v-bind="toolBoxProperties" />
        </div>
    </div>
</template>

<style scoped>
@import "theme/blue.scss";

.nav-item {
    cursor: pointer;
    text-decoration: none;
    list-style-type: none;
}

.left-column-disable {
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
    //width: 2.8rem;
    //min-width: 2.8rem;
    //max-width: 2.8rem;
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
