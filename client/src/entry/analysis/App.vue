<template>
    <div id="app">
        <div id="everything">
            <div id="background" />
            <Masthead
                v-if="showMasthead"
                id="masthead"
                :display-galaxy-brand="config.display_galaxy_brand"
                :brand="config.brand"
                :logo-url="config.logo_url"
                :logo-src="config.logo_src"
                :logo-src-secondary="config.logo_src_secondary"
                :tabs="tabs"
                :window-tab="windowTab"
                @open-url="openUrl" />
            <alert
                v-if="config.message_box_visible && config.message_box_content"
                id="messagebox"
                class="rounded-0 m-0 p-2"
                :variant="config.message_box_class || 'info'">
                <span class="fa fa-fw mr-1 fa-exclamation" />
                <span>{{ config.message_box_content }}</span>
            </alert>
            <alert
                v-if="config.show_inactivity_warning && config.inactivity_box_content"
                id="inactivebox"
                class="rounded-0 m-0 p-2"
                variant="alert-warning">
                <span class="fa fa-fw mr-1 fa-exclamation-triangle" />
                <span>{{ config.inactivity_box_content }}</span>
                <span>
                    <a class="ml-1" :href="resendUrl">Resend Verification</a>
                </span>
            </alert>
            <router-view @update:confirmation="confirmation = $event" />
        </div>
        <div id="dd-helper" />
        <Toast ref="toastRef" />
        <ConfirmDialog ref="confirmDialogRef" />
        <UploadModal ref="uploadModal" />
    </div>
</template>
<script>
import Modal from "mvc/ui/ui-modal";
import Masthead from "components/Masthead/Masthead.vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import { HistoryPanelProxy } from "components/History/adapters/HistoryPanelProxy";
import { fetchMenu } from "entry/analysis/menu";
import { WindowManager } from "layout/window-manager";
import { safePath } from "utils/redirect";
import Toast from "components/Toast";
import ConfirmDialog from "components/ConfirmDialog";
import UploadModal from "components/Upload/UploadModal.vue";
import { ref } from "vue";
import { setToastComponentRef } from "composables/toast";
import { setConfirmDialogComponentRef } from "composables/confirmDialog";
import { setGlobalUploadModal } from "composables/globalUploadModal";

export default {
    components: {
        Masthead,
        Toast,
        ConfirmDialog,
        UploadModal,
    },
    setup() {
        const toastRef = ref(null);
        setToastComponentRef(toastRef);
        const confirmDialogRef = ref(null);
        setConfirmDialogComponentRef(confirmDialogRef);
        const uploadModal = ref(null);
        setGlobalUploadModal(uploadModal);

        return { toastRef, confirmDialogRef, uploadModal };
    },
    data() {
        return {
            config: getGalaxyInstance().config,
            confirmation: null,
            resendUrl: `${getAppRoot()}user/resend_verification`,
            windowManager: new WindowManager(),
        };
    },
    computed: {
        tabs() {
            return fetchMenu(this.config);
        },
        showMasthead() {
            const masthead = this.$route.query.hide_masthead;
            if (masthead !== undefined) {
                return masthead.toLowerCase() != "true";
            }
            return true;
        },
        windowTab() {
            return this.windowManager.getTab();
        },
    },
    watch: {
        confirmation() {
            console.debug("App - Confirmation before route change: ", this.confirmation);
            this.$router.confirmation = this.confirmation;
        },
    },
    mounted() {
        const Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel = new HistoryPanelProxy();
        Galaxy.modal = new Modal.View();
        Galaxy.frame = this.windowManager;
    },
    created() {
        window.onbeforeunload = () => {
            if (this.confirmation || this.windowManager.beforeUnload()) {
                return "Are you sure you want to leave the page?";
            }
        };
    },
    methods: {
        openUrl(urlObj) {
            if (!urlObj.target) {
                this.$router.push(urlObj.url);
            } else {
                const url = safePath(urlObj.url);
                if (urlObj.target == "_blank") {
                    window.open(url);
                } else {
                    window.location = url;
                }
            }
        },
    },
};
</script>
