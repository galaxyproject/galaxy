<template>
    <div>
        <b-form @submit="submit">
            <b-card header="Change your password">
                <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText"/>
                <b-form-group v-if="user" label="Current Password">
                    <b-form-input type="password" v-model="current"/>
                </b-form-group>
                <b-form-group label="New Password">
                    <b-form-input type="password" v-model="password"/>
                </b-form-group>
                <b-form-group label="Confirm password">
                    <b-form-input type="password" v-model="confirm"/>
                </b-form-group>
                <b-button type="submit">Save new password</b-button>
            </b-card>
        </b-form>
    </div>
</template>
<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    data() {
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
            ev.preventDefault();
            axios
                .post(`${Galaxy.root}user/change_password`, {
                    token: this.token,
                    id: this.user,
                    current: this.current,
                    password: this.password,
                    confirm: this.confirm
                })
                .then(response => {
                    window.location = `${Galaxy.root}`;
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response && error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Login failed for unkown reason.";
                });
        }
    }
};
</script>
