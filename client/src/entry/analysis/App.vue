<template>
    <div id="app" :style="theme">
        <div id="everything">
            <div id="background" />
            <template v-if="!embedded">
                <Masthead
                    v-if="showMasthead"
                    id="masthead"
                    :brand="config.brand"
                    :logo-url="config.logo_url"
                    :logo-src="theme?.['--masthead-logo-img'] ?? config.logo_src"
                    :logo-src-secondary="theme?.['--masthead-logo-img-secondary'] ?? config.logo_src_secondary"
                    :window-tab="windowTab" />
                <Alert
                    v-if="config.message_box_visible && config.message_box_content"
                    id="messagebox"
                    class="rounded-0 m-0 p-2"
                    :variant="config.message_box_class || 'info'">
                    <span class="fa fa-fw mr-1 fa-exclamation" />
                    <!-- eslint-disable-next-line vue/no-restricted-syntax -- message_box_content only comes from the operator's galaxy.yml, and sites put embeds and styled banners in it -->
                    <span v-no-sanitize-html="config.message_box_content"></span>
                </Alert>
                <Alert
                    v-if="showInactivityWarning && config.inactivity_box_content"
                    id="inactivebox"
                    class="rounded-0 m-0 p-2"
                    variant="warning">
                    <span class="fa fa-fw mr-1 fa-exclamation-triangle" />
                    <span>{{ config.inactivity_box_content }}</span>
                    <span>
                        <a class="ml-1" :href="resendUrl">Resend Verification</a>
                    </span>
                </Alert>
            </template>

            <Alert v-if="(configLoadError || userLoadError) && !embedded" id="startup-load-error" variant="danger">
                <div v-if="configLoadError">Unable to load the Galaxy configuration: {{ configLoadError }}</div>
                <div v-if="userLoadError">Unable to load your user data: {{ userLoadError }}</div>
                <button type="button" class="btn btn-link p-0" @click="retryStartupLoad">Retry</button>
            </Alert>

            <router-view @update:confirmation="confirmation = $event" />
        </div>
        <template v-if="!embedded">
            <div id="dd-helper" />
            <GToast />
            <CommandPalette v-if="paletteEnabled" />
            <ConfirmDialog ref="confirmDialogRef" />
            <BroadcastsOverlay />
            <DragGhost />
            <template v-if="showMasthead">
                <WindowManagerWindow v-for="win in windowManagerStore.windows" :key="win.id" :window="win" />
            </template>
            <TourRunner v-if="currentTour?.id" :key="currentTour.id" :tour-id="currentTour.id" />
        </template>
    </div>
</template>
<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { type Router, useRoute, useRouter } from "vue-router";

import { getGalaxyInstance } from "@/app";
import { setConfirmDialogComponentRef } from "@/composables/confirmDialog";
import { useRouteQueryBool } from "@/composables/route";
import { useHasStagedUploads } from "@/composables/upload/useUploadStaging";
import { useCommandPalette } from "@/composables/useCommandPalette";
import { getAppRoot } from "@/onload";
import { useConfigStore } from "@/stores/configurationStore";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useHistoryStore } from "@/stores/historyStore";
import { useNotificationsStore } from "@/stores/notificationsStore";
import { useTourStore } from "@/stores/tourStore";
import { useUserStore } from "@/stores/userStore";
import { useWindowManagerStore } from "@/stores/windowManagerStore";
import { errorMessageAsString } from "@/utils/simple-error";

import Alert from "@/components/Alert.vue";
import GToast from "@/components/BaseComponents/GToast.vue";
import CommandPalette from "@/components/CommandPalette/CommandPalette.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import DragGhost from "@/components/DragGhost.vue";
import Masthead from "@/components/Masthead/Masthead.vue";
import BroadcastsOverlay from "@/components/Notifications/Broadcasts/BroadcastsOverlay.vue";
import TourRunner from "@/components/Tour/TourRunner.vue";
import WindowManagerWindow from "@/components/WindowManager/WindowManagerWindow.vue";

// router.js reads this before each navigation to decide whether to prompt about unsaved changes.
type ConfirmableRouter = Router & { confirmation?: boolean | null };

const galaxy = getGalaxyInstance();
const config = galaxy.config;
const resendUrl = `${getAppRoot()}user/resend_verification`;

const route = useRoute();
const router = useRouter() as ConfirmableRouter;

const tourStore = useTourStore();
const { currentTour } = storeToRefs(tourStore);

const userStore = useUserStore();
const { currentTheme } = storeToRefs(userStore);

const confirmDialogRef = ref<InstanceType<typeof ConfirmDialog> | null>(null);
// Vue 3 doesn't unwrap a ref stored in a ref, so pass the instance, not the ref.
watch(confirmDialogRef, (instance) => setConfirmDialogComponentRef(instance));

const windowManagerStore = useWindowManagerStore();
const hasStagedUploads = useHasStagedUploads();

// Unmounting the palette takes its ctrl/cmd+k listener with it, so an
// instance that turned it off runs none of its code. The open state
// outlives the component, so a logout that revokes access closes it.
const { paletteEnabled, closePalette } = useCommandPalette();
watch(paletteEnabled, (enabled) => {
    if (!enabled) {
        closePalette();
    }
});

// Treat any iframe context as embedded: scratchbook pops dataset
// displays into ``WinBox`` iframes that hit the same routes without
// an ``embed`` query param, and each one would otherwise open its own
// SSE + polling traffic, quickly saturating the HTTP/1.1 per-origin
// connection pool (e.g. ``test_scratchbook_window_persistence`` hangs
// indefinitely after two windows are open).
function isInIframe(): boolean {
    if (typeof window === "undefined") {
        return false;
    }
    try {
        return window.top !== window.self;
    } catch {
        // Cross-origin access throws -- that's definitely an iframe.
        return true;
    }
}
const inIframe = isInIframe();
const embeddedQuery = useRouteQueryBool("embed");
const embedded = computed(() => embeddedQuery.value || inIframe);
const historyStore = useHistoryStore();
if (!embedded.value) {
    historyStore.startWatchingHistory();
}

const configStore = useConfigStore();
const { loadError: configLoadError } = storeToRefs(configStore);

const userLoadError = ref("");
async function loadUser() {
    userLoadError.value = "";
    try {
        await userStore.loadUser();
    } catch (error) {
        userLoadError.value = errorMessageAsString(error);
    }
}

function retryStartupLoad() {
    if (configLoadError.value) {
        configStore.loadConfig();
    }
    if (userLoadError.value) {
        loadUser();
    }
}

watch(
    () => embedded.value,
    () => {
        if (embedded.value) {
            userStore.$reset();
        } else {
            loadUser();
        }
    },
    { immediate: true },
);

const confirmation = ref<boolean | null>(null);
watch(
    () => route.fullPath,
    () => {
        // sometimes, the confirmation is not cleared when the route changes
        // and the confirmation alert is shown needlessly
        if (confirmation.value) {
            confirmation.value = null;
        }

        // if we are on a tour route, start a tour if it wasn't already started or change tours
        const tourId = route.params.tourId;
        if (typeof tourId === "string" && tourId && tourId !== currentTour.value?.id) {
            tourStore.setTour(tourId);
        }
    },
    { immediate: true },
);
watch(confirmation, () => {
    console.debug("App - Confirmation before route change: ", confirmation.value);
    router.confirmation = confirmation.value;
});

const showInactivityWarning = computed(
    () => config.user_activation_on && galaxy.user?.id && !galaxy.user.get("active"),
);

const showMasthead = computed(() => {
    const hideMasthead = route.query.hide_masthead;
    return typeof hideMasthead !== "string" || hideMasthead.toLowerCase() != "true";
});

const theme = computed<Record<string, string> | null>(() => {
    if (embedded.value) {
        return null;
    }
    const themeKeys = Object.keys(config.themes);
    if (themeKeys.length > 0) {
        const userTheme = currentTheme.value;
        const selectedTheme = userTheme && themeKeys.includes(userTheme) ? userTheme : themeKeys[0];
        return config.themes[selectedTheme];
    }
    return null;
});

const windowTab = computed(() => windowManagerStore.getTab());

if (!embedded.value) {
    window.onbeforeunload = () => {
        if (confirmation.value || windowManagerStore.beforeUnload() || hasStagedUploads.value) {
            return "Are you sure you want to leave the page?";
        }
    };
}

onMounted(() => {
    if (!embedded.value) {
        if (showMasthead.value) {
            galaxy.frame = windowManagerStore;
            windowManagerStore.restore();
        }
        if (config.interactivetools_enable) {
            useEntryPointStore().startWatchingEntryPoints();
        }
        if (config.enable_notification_system) {
            useNotificationsStore().startWatchingNotifications();
        }
    }
});
</script>

<style lang="scss">
@import "../../style/scss/custom_theme_variables.scss";
</style>
