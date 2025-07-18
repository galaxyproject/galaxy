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
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import VerticalSeparator from "../Common/VerticalSeparator.vue";
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
const passwordState = ref<boolean | null>(null);
const loading = ref(false);
const messageText = ref("");
const messageVariant = ref<"info" | "danger">("info");
const connectExternalEmail = ref(urlParams.get("connect_external_email"));
const connectExternalLabel = ref(urlParams.get("connect_external_label"));
const connectExternalProvider = ref(urlParams.get("connect_external_provider"));
const confirmURL = ref(urlParams.has("confirm") && urlParams.get("confirm") == "true");

const excludeIdps = computed(() => (connectExternalProvider.value ? [connectExternalProvider.value] : undefined));

/** This decides if all login options should be displayed in column style
 * (one below the other) or horizontally.
 */
const loginColumnDisplay = computed(() => Boolean(props.showWelcomeWithLogin && props.welcomeUrl));

function toggleLogin() {
    emit("toggle-login");
}

async function submitLogin() {
    let redirect: string | null;
    passwordState.value = null;
    loading.value = true;

    if (connectExternalEmail.value) {
        login.value = connectExternalEmail.value;
    }

    if (localStorage.getItem("redirect_url")) {
        redirect = localStorage.getItem("redirect_url");
    } else {
        redirect = props.redirect ?? null;
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
    } catch (e) {
        loading.value = false;
        messageVariant.value = "danger";
        const message = errorMessageAsString(e, "Login failed for an unknown reason.");

        if (connectExternalProvider.value && message && message.toLowerCase().includes("invalid")) {
            messageText.value = message + " Try logging in to the existing account through an external provider below.";
        } else {
            messageText.value = message;
        }
        if (message === "Invalid password.") {
            passwordState.value = false;
        }
    }
}

function setRedirect(url: string) {
    localStorage.setItem("redirect_url", url);
}

async function resetLogin() {
    loading.value = true;
    try {
        const response = await axios.post(withPrefix("/user/reset_password"), { email: login.value });
        messageVariant.value = "info";
        messageText.value = response.data.message;
    } catch (e) {
        messageVariant.value = "danger";
        messageText.value = errorMessageAsString(e, "Password reset failed for an unknown reason.");
    } finally {
        loading.value = false;
    }
}

function returnToLogin() {
    router.push("/login/start");
}
</script>

<template>
    <div class="login-form">
        <div class="d-flex justify-content-md-center">
            <template v-if="!confirmURL">
                <div>
                    <BAlert :show="!!messageText" :variant="messageVariant">
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <span v-html="messageText" />
                    </BAlert>

                    <BAlert :show="!!connectExternalProvider" variant="info">
                        There already exists a user with the email <i>{{ connectExternalEmail }}</i
                        >. In order to associate this account with <i>{{ connectExternalLabel }}</i
                        >, you must first login to your existing account.
                    </BAlert>

                    <BForm id="login" @submit.prevent="submitLogin()">
                        <BCard no-body style="width: fit-content">
                            <BCardHeader v-if="!connectExternalProvider">
                                <span>{{ localize("Welcome to Galaxy, please log in") }}</span>
                            </BCardHeader>

                            <BCardBody :class="{ 'd-flex w-100': !loginColumnDisplay }">
                                <div>
                                    <!-- standard internal galaxy login -->
                                    <BFormGroup
                                        :label="localize('Public Name or Email Address')"
                                        label-for="login-form-name">
                                        <BFormInput
                                            v-if="!connectExternalProvider"
                                            id="login-form-name"
                                            v-model="login"
                                            required
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

                                    <BFormGroup :label="localize('Password')" label-for="login-form-password">
                                        <BFormInput
                                            id="login-form-password"
                                            v-model="password"
                                            required
                                            :state="passwordState"
                                            name="password"
                                            type="password"
                                            autocomplete="current-password" />

                                        <BFormText v-if="showResetLink" class="text-nowrap">
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

                                    <BButton
                                        v-localize
                                        name="login"
                                        type="submit"
                                        :disabled="loading"
                                        class="w-100 mt-1">
                                        {{ localize("Login") }}
                                    </BButton>
                                </div>

                                <template v-if="enableOidc">
                                    <VerticalSeparator v-if="!loginColumnDisplay">
                                        <span v-localize>or</span>
                                    </VerticalSeparator>

                                    <hr v-else class="w-100" />

                                    <div class="m-1 w-100">
                                        <!-- OIDC login-->
                                        <ExternalLogin
                                            login-page
                                            :exclude-idps="excludeIdps"
                                            :column-display="loginColumnDisplay" />
                                    </div>
                                </template>
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

            <div v-if="showWelcomeWithLogin && props.welcomeUrl" class="w-100">
                <BEmbed type="iframe" :src="withPrefix(props.welcomeUrl)" aspect="1by1" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.card-body {
    overflow: visible;
}
.login-form {
    margin: 0rem 10rem;
}
</style>
