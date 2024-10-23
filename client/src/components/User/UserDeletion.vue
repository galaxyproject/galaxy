<template>
    <UserPreferencesElement
        id="delete-account"
        icon="fa-radiation"
        title="Delete Account"
        description="Delete your account on this Galaxy server."
        @click="openModal">
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
    </UserPreferencesElement>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faRadiation } from "@fortawesome/free-solid-svg-icons";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import { userLogoutClient } from "utils/logout";
import { withPrefix } from "utils/redirect";
import Vue from "vue";

import UserPreferencesElement from "./UserPreferencesElement.vue";

library.add(faRadiation);

Vue.use(BootstrapVue);

export default {
    components: {
        UserPreferencesElement,
    },
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
        openModal() {
            this.$refs.modal.show();
        },
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
