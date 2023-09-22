<template>
    <b-row class="ml-3 mb-1">
        <i class="pref-icon pt-1 fa fa-lg fa-radiation" />
        <div class="pref-content pr-1">
            <a id="delete-account" href="javascript:void(0)"
                ><b v-b-modal.modal-prevent-closing v-localize>Delete Account</b></a
            >
            <div v-localize class="form-text text-muted">Delete your account on this Galaxy server.</div>
            <b-modal
                id="modal-prevent-closing"
                ref="modal"
                centered
                title="Account Deletion"
                title-tag="h2"
                @show="resetModal"
                @hidden="resetModal"
                @ok="handleOk">
                <p>
                    <b-alert variant="danger" :show="showDeleteError">{{ deleteError }}</b-alert>
                    <b>
                        This action cannot be undone. Your account will be permanently deleted, along with the data
                        contained in it.
                    </b>
                </p>
                <b-form ref="form" @submit.prevent="handleSubmit">
                    <b-form-group
                        :state="nameState"
                        label="Enter your user email for this account as confirmation."
                        label-for="Email"
                        invalid-feedback="Incorrect email">
                        <b-form-input id="name-input" v-model="name" :state="nameState" required></b-form-input>
                    </b-form-group>
                </b-form>
            </b-modal>
        </div>
    </b-row>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { userLogoutClient } from "utils/logout";
import { withPrefix } from "utils/redirect";

Vue.use(BootstrapVue);

export default {
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
        handleOk(bvModalEvt) {
            // Prevent modal from closing
            bvModalEvt.preventDefault();
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
