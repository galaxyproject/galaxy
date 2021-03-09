<!--
Temporary modal wrapper until I replace the entire UploadModal which desperately needs a rewrite.
Provides user and current history to modal because it currently has initialization sequence issues
-->

<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" :user="user" v-slot="{ currentHistoryId }">
            <b-modal
                :id="id"
                v-model="modalShow"
                :static="modalStatic"
                ref="uploadModal"
                header-class="no-separator"
                modal-class="ui-modal"
                dialog-class="upload-dialog"
                body-class="upload-dialog-body"
                no-enforce-focus
                hide-footer
            >
                <template v-slot:modal-header>
                    <h4 class="title" tabindex="0">{{ title | localize }}</h4>
                </template>

                <UploadModalContent
                    v-if="currentHistoryId"
                    :current-user-id="user.id"
                    :current-history-id="currentHistoryId"
                    v-bind="{ ...$props, ...$attrs }"
                    @dismiss="dismiss"
                    @hide="hide"
                    @cancel="cancel"
                />
            </b-modal>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import CurrentUser from "../providers/CurrentUser";
import UserHistories from "../History/providers/UserHistories";
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
            id: null,
            modalShow: false,
        };
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
    mounted() {
        this.eventHub.$on("upload:open", this.show);
        this.id = String(this._uid);
    },
};
</script>
