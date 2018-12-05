<template>
    <div>
        <b-alert :show="registration_warning_message" variant="danger">
            {{registration_warning_message}}
        </b-alert>
        <b-alert :show="messageShow" :variant="messageVariant" v-html="messageText"/>
        <b-form @submit.prevent="submit()">
            <b-card header="Create account">
                <b-form-group label="Email Address">
                    <b-form-input type="text" v-model="email"/>
                </b-form-group>
                <b-form-group label="Password">
                    <b-form-input type="password" v-model="password"/>
                </b-form-group>
                <b-form-group label="Confirm password">
                    <b-form-input type="password" v-model="confirm"/>
                </b-form-group>
                <b-form-group label="Public name">
                    <b-form-input type="text" v-model="username"/>
                    <b-form-text>Your public name is an identifier that will be used to generate addresses for information you share publicly. Public names must be at least three characters in length and contain only lower-case letters, numbers, dots, underscores, and dashes ('.', '_', '-').</b-form-text>
                </b-form-group>
                <b-form-group v-if="mailing_join_addr && smtp_server" label="Subscribe to mailing list">
                    <input type="checkbox" v-model="subscribe"/>
                </b-form-group>
                <b-button type="submit">Create</b-button>
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
    props: {
        registration_warning_message: {
            type: String,
            required: false
        },
        smtp_server: {
            type: String,
            required: false
        },
        mailing_join_addr: {
            type: String,
            required: false
        },
        redirect: {
            type: String,
            required: false
        }
    },
    data() {
        return {
            email: null,
            password: null,
            username: null,
            confirm: null,
            subscribe: null,
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
            axios
                .post(`${Galaxy.root}user/create`, this.$data)
                .then(response => {
                    if (response.data.message && response.data.status) {
                        alert(response.data.message);
                    }
                    window.location = this.redirect || `${Galaxy.root}`;
                })
                .catch(error => {
                    this.messageVariant = "danger";
                    let message = error.response.data && error.response.data.err_msg;
                    this.messageText = message || "Registration failed for an unknown reason.";
                });
        }
    }
};
</script>
