<template>
    <b-form @submit.prevent="submit">
        <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText" />
        <b-card header="Change your password">
            <b-form-group v-if="user" label="Current Password">
                <b-form-input type="password" v-model="current" />
            </b-form-group>
            <b-form-group label="New Password"> <b-form-input type="password" v-model="password" /> </b-form-group>
            <b-form-group label="Confirm password"> <b-form-input type="password" v-model="confirm" /> </b-form-group>
            <b-button type="submit">Save new password</b-button>
        </b-card>
    </b-form>
</template>
<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";

Vue.use(BootstrapVue);

export default {
    data() {
        let Galaxy = getGalaxyInstance();
        return {
            token: Galaxy.params.token,
            user: Galaxy.params.expired_user,
            password: null,
            confirm: null,
            current: null,
            messageText: Galaxy.params.message,
            messageVariant: Galaxy.params.status
        };
    },
    computed: {
        messageShow() {
            return this.messageText != null;
        }
    },
    methods: {
        submit: function(ev) {
            let urlRoot = getAppRoot();
            ev.preventDefault();
            axios
                .post(`${urlRoot}user/change_password`, {
                    token: this.token,
                    id: this.user,
                    current: this.current,
                    password: this.password,
                    confirm: this.confirm
                })
                .then(response => {
                    window.location = `${urlRoot}`;
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Password change failed for an unknown reason.";
                });
        }
    }
};
</script>
