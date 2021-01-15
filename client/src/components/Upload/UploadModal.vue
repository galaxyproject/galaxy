<!-- 
Temporary modal wrapper until I replace the entire UploadModal which desperately needs a rewrite.
Provides user and current history to modal because it currently has initialization sequence issues
-->

<template>
    <b-modal
        v-model="modalOpen"
        :static="modalStatic"
        header-class="no-separator"
        modal-class="ui-modal"
        dialog-class="upload-dialog"
        body-class="upload-dialog-body"
        ref="modal"
        no-enforce-focus
        hide-footer
        :id="id"
    >
        <template v-slot:modal-header>
            <h4 class="title" tabindex="0">{{ title | localize }}</h4>
        </template>

        <CurrentUser v-slot="{ user }">
            <UserHistories v-if="user && user.id" v-slot="{ currentHistoryId }">
                <UploadModalContent
                    ref="modal"
                    v-if="user.id && currentHistoryId"
                    :current-user-id="user.id"
                    :current-history-id="currentHistoryId"
                    v-bind="{ ...$props, ...$attrs }"
                    v-on="$listeners"
                    @dismiss="dismiss"
                />
            </UserHistories>
        </CurrentUser>
    </b-modal>
</template>

<script>
import CurrentUser from "../providers/CurrentUser";
import UserHistories from "../History/providers/UserHistories";
import UploadModalContent from "./UploadModalContent";
import { commonProps } from "./helpers";
import { eventHubMixin } from "components/plugins";

export default {
    mixins: [eventHubMixin],
    components: {
        CurrentUser,
        UserHistories,
        UploadModalContent,
    },
    props: {
        id: { type: String, default: "" },
        title: { type: String, default: "Download from web or upload from disk" },
        modalShow: { type: Boolean, default: false },
        modalStatic: { type: Boolean, default: true },
        ...commonProps,
    },
    computed: {
        modalOpen: {
            get() {
                return this.modalShow;
            },
            set(val) {
                this.$emit("update:modalShow", val);
            },
        },
    },
    methods: {
        show() {
            this.modalShow = true;
            this.$nextTick(this.tryMountingTabs);
        },
        hide() {
            this.modalShow = false;
        },
        cancel() {
            this.hide();
            this.$nextTick(() => {
                this.$bvModal.hide(this.id, "cancel");
                this.$destroy();
            });
        },
        dismiss() {
            // hide or cancel based on whether this is a singleton
            if (this.callback) {
                this.cancel();
            } else {
                this.hide();
            }
        },
    },
    created() {
        this.eventHub.$on("upload:show", this.show);
    },
};
</script>
