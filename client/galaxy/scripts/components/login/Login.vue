<template>
    <div>
        <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText"/>
        <b-form @submit.prevent="submit()">
            <b-card header="Welcome to Galaxy, please log in">
                <b-form-group label="Username or Email Address">
                    <b-form-input type="text" v-model="login"/>
                </b-form-group>
                <b-form-group label="Password">
                    <b-form-input type="password" v-model="password"/>
                    <b-form-text>Forgot password? Click here to <a @click="reset" href="#">reset</a> your password.</b-form-text>
                </b-form-group>
                <b-button type="submit">Login</b-button>
            </b-card>
        </b-form>
        <br>
        <b-form v-if="openid_providers && openid_providers.length > 0" @submit.prevent="submit('openid')">
            <b-card header="OpenID login">
                <b-form-group label="Enter a URL">
                    <b-form-input type="text" v-model="url"/>
                </b-form-group>
                <b-form-group label="Or select a provider:">
                     <b-form-select v-model="provider" :options="openid_providers"/>
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
        },
        openid_providers: {
            type: Array,
            required: false
        }
    },
    data() {
        return {
            login: null,
            password: null,
            url: null,
            provider: null,
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
        submit: function(method) {
            let data = null;
            if (method == "openid") {
                data = {openid_provider: this.provider, openid_url: this.url};
            } else {
                data = {login: this.login, password: this.password};
            }
            axios
                .post(`${Galaxy.root}user/login`, data)
                .then(response => {
                    if (response.data.message && response.data.status) {
                        alert(response.data.message);
                    }
                    if (response.data.expired_user) {
                        window.location = `${Galaxy.root}root/login?expired_user=${response.data.expired_user}`;
                    } else if (response.data.redirect) {
                        window.location = response.data.redirect;
                    } else {
                        window.location = `${Galaxy.root}`;
                    }
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Login failed for an unknown reason.";
                });
        },
        reset: function(ev) {
            ev.preventDefault();
            axios
                .post(`${Galaxy.root}user/reset_password`, {email: this.login})
                .then(response => {
                    this.messageVariant = "info";
                    this.messageText = response.data.message;
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Password reset failed for an unknown reason.";
                });
        }
    }
};
</script>
