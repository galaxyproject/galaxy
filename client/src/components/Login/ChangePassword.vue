<template>
    <GForm @submit.prevent="submit">
        <GAlert v-if="!!message" :variant="variant" show>
            {{ message }}
        </GAlert>
        <GCard header="Change your password">
            <GFormGroup v-if="expiredUser" label="Current Password">
                <GInput v-model="current" type="password" />
            </GFormGroup>
            <GFormGroup label="New Password"> <GInput v-model="password" type="password" /> </GFormGroup>
            <GFormGroup label="Confirm password"> <GInput v-model="confirm" type="password" /> </GFormGroup>
            <GButton type="submit">Save new password</GButton>
        </GCard>
    </GForm>
</template>
<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import Vue from "vue";

import { GAlert, GButton, GCard, GForm, GFormGroup, GInput } from "@/component-library";

Vue.use(BootstrapVue);

export default {
    components: {
        GAlert,
        GButton,
        GCard,
        GForm,
        GFormGroup,
        GInput,
    },
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
                    const message = error.response && error.response.data && error.response.data.err_msg;
                    this.message = message || "Password change failed for an unknown reason.";
                });
        },
    },
};
</script>
