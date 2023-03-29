<script setup>
import { getGalaxyInstance } from "app";
import { useUserStore } from "@/stores/userStore";
import { WindowManager } from "@/layout/window-manager";
import { useRoute, useRouter } from "vue-router/composables";
import { computed, ref } from "vue";
import UploadItem from "./Items/UploadItem.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox.vue";
import ActivityItem from "./ActivityItem";

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
        <b-nav vertical class="activity-bar flex-nowrap p-1">
            <ActivityItem
                id="tools"
                icon="wrench"
                title="Tools"
                tooltip="Search and run tools"
                :is-active="sidebarIsActive('search')"
                @click="onToggleSidebar('search')" />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
            <upload-item />
        </b-nav>
        <div class="activity-footer">
            <b-nav vertical class="flex-nowrap p-1">
                <ActivityItem id="settings" icon="cog" title="Configure" tooltip="Search and run tools" />
            </b-nav>
        </div>
        <div v-show="sidebarIsActive('search')" key="search">
            <ToolBox class="left-column" v-bind="toolBoxProperties" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.left-column {
    width: 15rem;
}

.activity-bar {
    background: $panel-bg-color;
    overflow-y: auto;
    width: 4rem;
}

.activity-bar::-webkit-scrollbar {
    display: none;
}

.activity-footer {
    @extend .activity-bar;
    position: absolute;
    left: 0;
    bottom: 0px;
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
