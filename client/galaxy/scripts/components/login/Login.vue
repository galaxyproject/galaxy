<template>
    <div>
        <b-form @submit="submit">
            <b-card header="Welcome to Galaxy, please log in">
                <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText"/>
                <b-form-group label="Username or Email Address">
                    <b-form-input type="text" v-model="username"/>
                </b-form-group>
                <b-form-group label="Password">
                    <b-form-input type="password" v-model="password"/>
                    <b-form-text>Forgot password? Click here to <a @click="reset" href="#">reset</a> your password.</b-form-text>
                </b-form-group>
                <b-button type="submit">Login</b-button>
            </b-card>
        </b-form>
        <br>
        <b-form @submit="submit">
            <b-card header="OpenID login">
                <b-alert :show="openidMessageShow" :variant="openidMessageVariant" v-html="openidMessageText"/>
                <b-form-group label="Username or Email Address">
                    <b-form-input type="text" v-model="openidUsername"/>
                </b-form-group>
                <b-form-group label="Password">
                    <b-form-input type="password" v-model="openidPassword"/>
                </b-form-group>
                <b-button type="submit">Login with OpenID</b-button>
            </b-card>
        </b-form>
        <br>
        <b-embed v-if="show_welcome_with_login"
            type="iframe"
            aspect="16by9"
            :src="welcome_url"
        ></b-embed>
    </div>
</template>
<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        show_welcome_with_login: {
            type: Boolean,
            required: false
        },
        welcome_url: {
            type: String,
            required: false
        }
    },
    data() {
        return {
            username: null,
            password: null,
            messageText: null,
            messageVariant: null
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
                .post(`${Galaxy.root}user/login`, {username: this.username, password: this.password})
                .then(response => {
                    if (response.data.message && response.data.status) {
                        alert(response.data.message);
                    }
                    window.location = `${Galaxy.root}`;
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Login failed for unkown reason.";
                });
        },
        reset: function(ev) {
            ev.preventDefault();
            axios
                .post(`${Galaxy.root}api/users/reset_password`, {email: this.username})
                .then(response => {
                    this.messageVariant = "info";
                    this.messageText = response.data.message;
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Password reset failed for unkown reason.";
                });
        }
    }
};
</script>
