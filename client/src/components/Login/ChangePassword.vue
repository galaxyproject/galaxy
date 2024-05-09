<template>
    <b-form @submit.prevent="submit">
        <b-alert v-if="!!message" :variant="variant" show>
            {{ message }}
        </b-alert>
        <b-card header="Change your password">
            <b-form-group v-if="expiredUser" label="Current Password">
                <b-form-input v-model="current" type="password" />
            </b-form-group>
            <b-form-group label="New Password"> <b-form-input v-model="password" type="password" /> </b-form-group>
            <b-form-group label="Confirm password"> <b-form-input v-model="confirm" type="password" /> </b-form-group>
            <b-button type="submit">Save new password</b-button>
        </b-card>
    </b-form>
</template>
<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import { errorMessageAsString } from "utils/simple-error";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    props: {
        token: {
            type: String,
            default: null,
        },
        expiredUser: {
            type: String,
            default: null,
        },
        messageText: {
            type: String,
            default: null,
        },
        messageVariant: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            password: null,
            confirm: null,
            current: null,
            message: this.messageText,
            variant: this.messageVariant,
        };
    },
    methods: {
        submit() {
            axios
                .post(withPrefix("/user/change_password"), {
                    token: this.token,
                    id: this.expiredUser,
                    current: this.current,
                    password: this.password,
                    confirm: this.confirm,
                })
                .then((response) => {
                    window.location = withPrefix(`/`);
                })
                .catch((error) => {
                    this.variant = "danger";
                    this.message = errorMessageAsString(error, "Password change failed for an unknown reason.");
                });
        },
    },
};
</script>
