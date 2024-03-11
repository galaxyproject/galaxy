<script setup lang="ts">
import axios from "axios";
import {
    BAlert,
    BButton,
    BCard,
    BCardBody,
    BCardFooter,
    BCardHeader,
    BEmbed,
    BForm,
    BFormGroup,
    BFormInput,
    BFormText,
} from "bootstrap-vue";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";

import NewUserConfirmation from "@/components/Login/NewUserConfirmation.vue";
import ExternalLogin from "@/components/User/ExternalIdentities/ExternalLogin.vue";

interface Props {
    sessionCsrfToken: string;
    redirect?: string;
    termsUrl?: string;
    welcomeUrl?: string;
    enableOidc?: boolean;
    showResetLink?: boolean;
    allowUserCreation?: boolean;
    showWelcomeWithLogin?: boolean;
    registrationWarningMessage?: string;
}

const props = withDefaults(defineProps<Props>(), {
    showResetLink: true,
    redirect: undefined,
    termsUrl: undefined,
    welcomeUrl: undefined,
    registrationWarningMessage: undefined,
});

const emit = defineEmits<{
    (e: "toggle-login"): void;
    (e: "set-redirect", url: string): void;
}>();

const router = useRouter();

const urlParams = new URLSearchParams(window.location.search);

const login = ref("");
const password = ref(null);
const messageText = ref("");
const labelPassword = ref(localize("Password"));
const messageVariant = ref<"info" | "danger">("info");
const headerWelcome = ref(localize("Welcome to Galaxy, please log in"));
const labelNameAddress = ref(localize("Public Name or Email Address"));
const connectExternalEmail = ref(urlParams.get("connect_external_email"));
const connectExternalLabel = ref(urlParams.get("connect_external_label"));
const connectExternalProvider = ref(urlParams.get("connect_external_provider"));
const confirmURL = ref(urlParams.has("confirm") && urlParams.get("confirm") == "true");

function toggleLogin() {
    emit("toggle-login");
}

async function submitLogin() {
    let redirect: string | null;

    if (connectExternalEmail.value) {
        login.value = connectExternalEmail.value;
    }

    if (localStorage.getItem("redirect_url")) {
        redirect = localStorage.getItem("redirect_url");
    } else {
        redirect = props.redirect;
    }

    try {
        const response = await axios.post(withPrefix("/user/login"), {
            login: login.value,
            password: password.value,
            redirect: redirect,
            session_csrf_token: props.sessionCsrfToken,
        });

        if (response.data.message && response.data.status) {
            alert(response.data.message);
        }

        if (response.data.expired_user) {
            window.location.href = withPrefix(`/root/login?expired_user=${response.data.expired_user}`);
        } else if (connectExternalProvider.value) {
            window.location.href = withPrefix("/user/external_ids?connect_external=true");
        } else if (response.data.redirect) {
            window.location.href = withPrefix(encodeURI(response.data.redirect));
        } else {
            window.location.href = withPrefix("/");
        }
    } catch (error: any) {
        messageVariant.value = "danger";
        const message = error.response && error.response.data && error.response.data.err_msg;

        if (connectExternalProvider.value && message && message.toLowerCase().includes("invalid")) {
            messageText.value = message + " Try logging in to the existing account through an external provider below.";
        } else {
            messageText.value = message || "Login failed for an unknown reason.";
        }
    }
}

function setRedirect(url: string) {
    localStorage.setItem("redirect_url", url);
}

async function resetLogin() {
    try {
        const response = await axios.post(withPrefix("/user/reset_password"), { email: login.value });
        messageVariant.value = "info";
        messageText.value = response.data.message;
    } catch (error: any) {
        messageVariant.value = "danger";
        const errMsg = error.response.data && error.response.data.err_msg;
        messageText.value = errMsg || "Password reset failed for an unknown reason.";
    }
}

function returnToLogin() {
    router.push("/login/start");
}
</script>

<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <template v-if="!confirmURL">
                <div class="col col-lg-6">
                    <BAlert :show="!!messageText" :variant="messageVariant">
                        <span v-html="messageText" />
                    </BAlert>

                    <BAlert :show="!!connectExternalProvider" variant="info">
                        There already exists a user with the email <i>{{ connectExternalEmail }}</i
                        >. In order to associate this account with <i>{{ connectExternalLabel }}</i
                        >, you must first login to your existing account.
                    </BAlert>

                    <BForm id="login" @submit.prevent="submitLogin()">
                        <BCard no-body>
                            <BCardHeader v-if="!connectExternalProvider">
                                <span>{{ headerWelcome }}</span>
                            </BCardHeader>

                            <BCardBody>
                                <div>
                                    <!-- standard internal galaxy login -->
                                    <BFormGroup :label="labelNameAddress" label-for="login-form-name">
                                        <BFormInput
                                            v-if="!connectExternalProvider"
                                            id="login-form-name"
                                            v-model="login"
                                            name="login"
                                            type="text" />
                                        <BFormInput
                                            v-else
                                            id="login-form-name"
                                            disabled
                                            :value="connectExternalEmail"
                                            name="login"
                                            type="text" />
                                    </BFormGroup>

                                    <BFormGroup :label="labelPassword" label-for="login-form-password">
                                        <BFormInput
                                            id="login-form-password"
                                            v-model="password"
                                            name="password"
                                            type="password" />

                                        <BFormText v-if="showResetLink">
                                            <span v-localize>Forgot password?</span>

                                            <a
                                                v-localize
                                                href="javascript:void(0)"
                                                role="button"
                                                @click.prevent="resetLogin">
                                                Click here to reset your password.
                                            </a>
                                        </BFormText>
                                    </BFormGroup>

                                    <BButton v-localize name="login" type="submit">Login</BButton>
                                </div>
                                <div v-if="enableOidc">
                                    <!-- OIDC login-->
                                    <ExternalLogin login-page :exclude-idps="[connectExternalProvider]" />
                                </div>
                            </BCardBody>

                            <BCardFooter>
                                <span v-if="!connectExternalProvider">
                                    Don't have an account?
                                    <span v-if="allowUserCreation">
                                        <a
                                            id="register-toggle"
                                            v-localize
                                            href="javascript:void(0)"
                                            role="button"
                                            @click.prevent="toggleLogin">
                                            Register here.
                                        </a>
                                    </span>
                                    <span v-else>
                                        Registration for this Galaxy instance is disabled. Please contact an
                                        administrator for assistance.
                                    </span>
                                </span>
                                <span v-else>
                                    Do not wish to connect to an external provider?
                                    <a href="javascript:void(0)" role="button" @click.prevent="returnToLogin">
                                        Return to login here.
                                    </a>
                                </span>
                            </BCardFooter>
                        </BCard>
                    </BForm>
                </div>
            </template>
            <template v-else>
                <NewUserConfirmation
                    :registration-warning-message="registrationWarningMessage"
                    :terms-url="termsUrl"
                    @setRedirect="setRedirect" />
            </template>

            <div v-if="showWelcomeWithLogin && props.welcomeUrl" class="col">
                <BEmbed type="iframe" :src="withPrefix(props.welcomeUrl)" aspect="1by1" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.card-body {
    overflow: visible;
}
</style>
