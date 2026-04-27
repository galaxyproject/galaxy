<script setup>
import { faChevronLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { usePanels } from "@/composables/usePanels";
import { useUserStore } from "@/stores/userStore";

import CenterFrame from "./CenterFrame.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import HistoryIndex from "@/components/History/Index.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";

const router = useRouter();
const showCenter = ref(false);
const { showPanels } = usePanels();

const historyPanel = ref(null);

const { historyPanelWidth } = storeToRefs(useUserStore());

// methods
function hideCenter() {
    showCenter.value = false;
}

function onShow(showPanel) {
    if (historyPanel.value) {
        historyPanel.value.show = showPanel;
    }
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
        <FlexPanel v-if="showPanels" ref="historyPanel" side="right" :reactive-width.sync="historyPanelWidth">
            <template v-slot:closed-button="{ open }">
                <GButton
                    class="history-expand-button"
                    data-description="history panel expand button"
                    size="small"
                    @click="open">
                    <FontAwesomeIcon fixed-width :icon="faChevronLeft" />
                    <transition name="slide">
                        <span>History</span>
                    </transition>
                </GButton>
            </template>
            <HistoryIndex @show="onShow" />
        </FlexPanel>
        <DragAndDropModal />
    </div>
</template>

<style scoped lang="scss">
.history-expand-button {
    display: flex;
    align-items: center;
    height: 1.6rem;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
    position: absolute;
    top: 0;
    right: 0;
    z-index: 100;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;

    span {
        opacity: 0;
        max-width: 0;
        overflow: hidden;
        transition: all 0.3s ease;
    }

    &:hover span {
        opacity: 1;
        max-width: 100px;
    }
}

// Slide transition for History text
.slide-enter-active,
.slide-leave-active {
    transition: all 0.3s ease;
    overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
    opacity: 0;
    transform: translateX(10px);
    max-width: 0;
}

.slide-enter-to,
.slide-leave-from {
    opacity: 1;
    transform: translateX(0);
    max-width: 100px;
}
</style>
