<!--
Temporary modal wrapper until I replace the entire UploadModal which desperately needs a rewrite.
Provides user and current history to modal because it currently has initialization sequence issues
-->

<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ currentHistoryId }" :user="user">
            <b-modal
                v-model="modalShow"
                :static="modalStatic"
                header-class="no-separator"
                modal-class="ui-modal"
                dialog-class="upload-dialog"
                body-class="upload-dialog-body"
                no-enforce-focus
                hide-footer>
                <template v-slot:modal-header>
                    <h4 class="title" tabindex="0">{{ title | localize }}</h4>
                </template>

                <UploadModalContent
                    v-if="currentHistoryId"
                    :current-user-id="user.id"
                    :current-history-id="currentHistoryId"
                    v-bind="{ ...$props, ...$attrs }"
                    @dismiss="dismiss" />
            </b-modal>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import CurrentUser from "../providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import UploadModalContent from "./UploadModalContent";
import { commonProps } from "./helpers";

export default {
    components: {
        CurrentUser,
        UserHistories,
        UploadModalContent,
    },
    props: {
        title: { type: String, default: "Download from web or upload from disk" },
        modalStatic: { type: Boolean, default: true },
        ...commonProps,
    },
    data() {
        return {
            modalShow: false,
        };
    },
    watch: {
        modalShow() {
            this.setIframeEvents(this.modalShow);
        },
    },
    mounted() {
        this.show();
        // handles subsequent external requests to re-open a re-used modal
        this.$root.$on("openUpload", this.show);
    },
    methods: {
        show() {
            this.modalShow = true;
        },
        hide() {
            this.modalShow = false;
        },
        dismiss(result) {
            if (undefined !== result) {
                this.$root.$emit("uploadResult", result);
            }
            this.hide();
        },
        /** Disable mouse events in iframe to prevent interference with uploader drop box */
        setIframeEvents(disableEvents) {
            const element = document.getElementById("galaxy_main");
            if (element) {
                element.style["pointer-events"] = disableEvents ? "none" : "auto";
            } else {
                console.warn("UploadModal::setIframeEvents - `galaxy_main` not found.");
            }
        },
    },
};
</script>
