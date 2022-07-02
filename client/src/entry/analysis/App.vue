<template>
    <body scroll="no" class="full-content">
        <div id="everything">
            <div id="background" />
            <Masthead
                v-if="showMasthead"
                id="masthead"
                :masthead-state="mastheadState"
                :display-galaxy-brand="config.display_galaxy_brand"
                :brand="config.brand"
                :brand-link="staticUrlToPrefixed(config.logo_url)"
                :brand-image="staticUrlToPrefixed(config.logo_src)"
                :brand-image-secondary="staticUrlToPrefixed(config.logo_src_secondary)"
                :menu-options="config" />
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
    </body>
</template>
<script>
import { MastheadState } from "layout/masthead";
import Modal from "mvc/ui/ui-modal";
import Masthead from "components/Masthead/Masthead.vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";
import { HistoryPanelProxy } from "components/History/adapters/HistoryPanelProxy";

export default {
    components: {
        Masthead,
    },
    mounted() {
        const Galaxy = getGalaxyInstance();
        Galaxy.currHistoryPanel = new HistoryPanelProxy();
        Galaxy.modal = new Modal.View();
    },
    data() {
        return {
            config: getGalaxyInstance().config,
            confirmation: null,
            mastheadState: new MastheadState(),
            resendUrl: `${getAppRoot()}user/resend_verification`,
        };
    },
    watch: {
        confirmation() {
            console.debug("App - Confirmation before route change: ", this.confirmation);
            this.$router.confirmation = this.confirmation;
        },
    },
    created() {
        window.onbeforeunload = () => {
            if (this.confirmation || this.mastheadState.windowManager.beforeUnload()) {
                return "Are you sure you want to leave the page?";
            }
        };
    },
    computed: {
        showMasthead() {
            const masthead = this.$route.query.hide_masthead;
            if (masthead !== undefined) {
                return masthead.toLowerCase() != "true";
            }
            return true;
        },
    },
    methods: {
        staticUrlToPrefixed(url) {
            return url?.startsWith("/") ? `${getAppRoot()}${url.substring(1)}` : url;
        },
    },
};
</script>
