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
        <b-nav vertical class="acitivity-bar flex-nowrap p-1">
            <ActivityItem
                id="tools"
                icon="wrench"
                title="Tools"
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
        <div class="acitivity-bar" style="background: red; position: absolute; left: 0; bottom: 0px">
            <b-nav vertical class="bottom-bar flex-nowrap p-1 m-1">
                <b-nav-item>
                    <template>
                        <span class="nav-icon fa fa-gear" />
                    </template>
                </b-nav-item>
                <b-nav-item>
                    <template>
                        <span class="nav-icon fa fa-caret-down" />
                    </template>
                </b-nav-item>
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

.acitivity-bar {
    background: $panel-bg-color;
    overflow-y: auto;
    width: 4rem;
}

.acitivity-bar::-webkit-scrollbar {
    display: none;
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
