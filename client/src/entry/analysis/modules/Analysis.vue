<script setup>
import { storeToRefs } from "pinia";
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";
import { usePanels } from "@/composables/usePanels";
import { useUserStore } from "@/stores/userStore";

import CenterFrame from "./CenterFrame.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import HistoryIndex from "@/components/History/Index.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ToolPanel from "@/components/Panels/ToolPanel.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";
import Login from "@/entry/analysis/modules/Login.vue";

const router = useRouter();
const showCenter = ref(false);
const { showActivityBar, showToolbox, showPanels } = usePanels();
const { isAnonymous } = storeToRefs(useUserStore());
const { config, isConfigLoaded } = useConfig();

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
        <ActivityBar v-if="showActivityBar" />
        <FlexPanel v-if="showToolbox" side="left">
            <ToolPanel />
        </FlexPanel>
        <!-- TODO: fix bug where center span pushes right panel out of view (tool: 'gene2exon1') -->
        <span class="d-flex flex-column">
            <Login v-if="isAnonymous && isConfigLoaded && config.show_login_on_header" class="p-3" show-as-box />
            <div id="center" class="overflow-auto p-3 w-100 h-100 d-block">
                <CenterFrame v-show="showCenter" id="galaxy_main" class="flex-grow-1" @load="onLoad" />
                <router-view v-show="!showCenter" :key="$route.fullPath" class="h-100" />
            </div>
        </span>
        <FlexPanel v-if="showPanels" side="right">
            <HistoryIndex />
        </FlexPanel>
        <DragAndDropModal />
    </div>
</template>
