<script setup lang="ts">
import Alert from "@/components/Alert.vue";
import Modal from "@/mvc/ui/ui-modal";
import Masthead from "components/Masthead/Masthead.vue";
import { getGalaxyInstance } from "@/app";
import { getAppRoot } from "@/onload";
import { HistoryPanelProxy } from "@/components/History/adapters/HistoryPanelProxy";
import { fetchMenu } from "@/entry/analysis/menu";
import { WindowManager } from "@/layout/window-manager";
import { withPrefix } from "@/utils/redirect";
import Toast from "@/components/Toast";
import ConfirmDialog from "@/components/ConfirmDialog";
import UploadModal from "@/components/Upload/UploadModal.vue";
import { ref, computed, watch, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useUserStore } from "@/stores/userStore";
import { useHistoryStore } from "@/stores/historyStore";
import { setToastComponentRef } from "@/composables/toast";
import { setConfirmDialogComponentRef } from "@/composables/confirmDialog";
import { setGlobalUploadModal } from "@/composables/globalUploadModal";
import { useRoute, useRouter } from "vue-router/composables";
import { useConfig } from "@/composables/config";

const userStore = useUserStore();
const router = useRouter();
const route = useRoute();

const { config, isLoaded } = useConfig();
const { currentTheme } = storeToRefs(userStore);
const { currentHistory } = storeToRefs(useHistoryStore());

userStore.loadUser();

// Configure application toast
const toastRef = ref(null);
setToastComponentRef(toastRef);

// Configure application confirmation
const confirmation = ref(null);
const confirmDialogRef = ref(null);
setConfirmDialogComponentRef(confirmDialogRef);

// Configure uploadModal
const uploadModal = ref(null);
setGlobalUploadModal(uploadModal);

const windowManager = new WindowManager();
const resendUrl = `${getAppRoot()}user/resend_verification`;

const tabs = computed(() => {
    return fetchMenu(config.value);
});

const showMasthead = computed(() => {
    return route.query.hide_masthead !== "true";
});

const theme = computed(() => {
    if (isLoaded && config?.value?.themes) {
        const themeKeys = Object.keys(config.value.themes);
        if (themeKeys.length > 0) {
            if (currentTheme.value && themeKeys.includes(currentTheme.value)) {
                return config.value.themes[currentTheme.value];
            } else {
                return config.value.themes[themeKeys[0]!];
            }
        }
    }
    return null;
});

const windowTab = computed(() => {
    return windowManager.getTab();
});

watch(confirmation, () => {
    console.debug("App - Confirmation before route change: ", confirmation.value);
    // We patch a confirmation value, see router-push.js
    (router as any).confirmation = confirmation.value;
});

watch(currentHistory, () => {
    const Galaxy = getGalaxyInstance();
    Galaxy.currHistoryPanel.syncCurrentHistoryModel(currentHistory.value);
});

onMounted(() => {
    const Galaxy = getGalaxyInstance();
    Galaxy.currHistoryPanel = new HistoryPanelProxy();
    Galaxy.modal = new Modal.View();
    Galaxy.frame = windowManager;
});

function openUrl(urlObj: any) {
    if (!urlObj.target) {
        router.push(urlObj.url);
    } else {
        const url = withPrefix(urlObj.url);
        if (urlObj.target == "_blank") {
            window.open(url);
        } else {
            window.location.href = url;
        }
    }
}

// created
window.onbeforeunload = () => {
    if (confirmation.value || windowManager.beforeUnload()) {
        return "Are you sure you want to leave the page?";
    }
};
</script>

<template>
    <div id="app" :style="theme">
        <div id="everything">
            <div id="background" />
            <Masthead
                v-if="showMasthead"
                id="masthead"
                :brand="config.brand"
                :logo-url="config.logo_url"
                :logo-src="theme?.['--masthead-logo-img'] ?? config.logo_src"
                :logo-src-secondary="theme?.['--masthead-logo-img-secondary'] ?? config.logo_src_secondary"
                :tabs="tabs"
                :window-tab="windowTab"
                @open-url="openUrl" />
            <Alert
                v-if="config.message_box_visible && config.message_box_content"
                id="messagebox"
                class="rounded-0 m-0 p-2"
                :variant="config.message_box_class || 'info'">
                <span class="fa fa-fw mr-1 fa-exclamation" />
                <!-- eslint-disable-next-line vue/no-v-html -->
                <span v-html="config.message_box_content"></span>
            </Alert>
            <Alert
                v-if="config.show_inactivity_warning && config.inactivity_box_content"
                id="inactivebox"
                class="rounded-0 m-0 p-2"
                variant="warning">
                <span class="fa fa-fw mr-1 fa-exclamation-triangle" />
                <span>{{ config.inactivity_box_content }}</span>
                <span>
                    <a class="ml-1" :href="resendUrl">Resend Verification</a>
                </span>
            </Alert>
            <router-view @update:confirmation="confirmation = $event" />
        </div>
        <div id="dd-helper" />
        <Toast ref="toastRef" />
        <ConfirmDialog ref="confirmDialogRef" />
        <UploadModal ref="uploadModal" />
    </div>
</template>
<style lang="scss">
@import "custom_theme_variables.scss";
</style>
