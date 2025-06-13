<template>
    <div class="ml-3 mb-1 d-flex">
        <i class="pref-icon pt-1 fa fa-lg fa-radiation" />
        <div class="pref-content pr-1">
            <GLink id="delete-account" @click="showModal = true">
                <b v-localize>Delete Account</b>
            </GLink>
            <div v-localize class="form-text text-muted">Delete your account on this Galaxy server.</div>
            <GModal
                id="modal-prevent-closing"
                title="Account Deletion"
                :show.sync="showModal"
                confirm
                ok-text="Delete Account"
                :close-on-ok="false"
                @open="resetModal"
                @close="resetModal"
                @ok="handleOk">
                <p>
                    <b-alert variant="danger" :show="showDeleteError">{{ deleteError }}</b-alert>
                    <b>
                        This action cannot be undone. Your account will be permanently deleted, along with the data
                        contained in it.
                    </b>
                </p>
                <GForm ref="form" @submit.prevent="handleSubmit">
                    <GFormLabel
                        :state="nameState"
                        title="Enter your user email for this account as confirmation."
                        invalid-feedback="Incorrect email">
                        <GFormInput id="name-input" v-model="name" required></GFormInput>
                    </GFormLabel>
                </GForm>
            </GModal>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import { userLogoutClient } from "utils/logout";
import { withPrefix } from "utils/redirect";
import Vue from "vue";

import GForm from "@/components/BaseComponents/Form/GForm.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GFormLabel from "@/components/BaseComponents/Form/GFormLabel.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

Vue.use(BootstrapVue);

export default {
    components: { GLink, GModal, GForm, GFormLabel, GFormInput },
    props: {
        userId: {
            type: String,
            required: true,
        },
        email: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            showModal: false,
            name: "",
            nameState: null,
            deleteError: "",
        };
    },
    computed: {
        showDeleteError() {
            return this.deleteError !== "";
        },
    },
    methods: {
        checkFormValidity() {
            const valid = this.$refs.form.checkValidity();
            this.nameState = valid;
            return valid;
        },
        resetModal() {
            this.name = "";
            this.nameState = null;
        },
        handleOk() {
            // Trigger submit handler
            this.handleSubmit();
        },
        async handleSubmit() {
            if (!this.checkFormValidity()) {
                return false;
            }
            if (this.email === this.name) {
                this.nameState = true;
                try {
                    await axios.delete(withPrefix(`/api/users/${this.userId}`));
                } catch (e) {
                    if (e.response.status === 403) {
                        this.deleteError =
                            "User deletion must be configured on this instance in order to allow user self-deletion.  Please contact an administrator for assistance.";
                        return false;
                    }
                }
                userLogoutClient();
            } else {
                this.nameState = false;
                return false;
            }
        },
    },
};
</script>

<style scoped>
@import "user-styles.scss";
</style>
