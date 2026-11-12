<script setup lang="ts">
import { useElementSize } from "@vueuse/core";
import axios from "axios";
import {
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
import { useRouter } from "vue-router";

import { SKIP_PENDING_REQUESTS_HEADER } from "@/api/pendingRequests";
import { discardActiveConnectionsBeforeAuthNavigation } from "@/composables/useAuthNavigation";
import localize from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "../BaseComponents/GButton.vue";
import GLink from "../BaseComponents/GLink.vue";
import VerticalSeparator from "../Common/VerticalSeparator.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
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
    disableLocalAccounts?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    showResetLink: true,
    redirect: undefined,
    termsUrl: undefined,
    welcomeUrl: undefined,
    registrationWarningMessage: undefined,
    disableLocalAccounts: false,
});

const router = useRouter();

const urlParams = new URLSearchParams(window.location.search);

const login = ref("");
const password = ref(null);
const passwordState = ref<boolean | null>(null);
const loading = ref(false);
const networkMessage = urlParams.get("message") || "";
const messageText = ref(networkMessage);
const statusParam = urlParams.get("status");
const messageVariant = ref<"info" | "danger">(statusParam === "info" ? "info" : "danger");
const connectExternalEmail = ref(urlParams.get("connect_external_email"));
const connectExternalLabel = ref(urlParams.get("connect_external_label"));
const connectExternalProvider = ref(urlParams.get("connect_external_provider"));
const confirmURL = ref(urlParams.has("confirm") && urlParams.get("confirm") == "true");

const excludeIdps = computed(() => (connectExternalProvider.value ? [connectExternalProvider.value] : undefined));

const showWelcome = computed(() => Boolean(props.showWelcomeWithLogin && props.welcomeUrl));
const loginFormRoot = ref<HTMLElement | null>(null);
const { width: loginFormWidth } = useElementSize(loginFormRoot);
const isNarrow = computed(() => loginFormWidth.value > 0 && loginFormWidth.value < 800);

/** Stack login options vertically beside the welcome page or on narrow screens. */
const loginColumnDisplay = computed(() => showWelcome.value || isNarrow.value);

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

    // Stop polling and abort in-flight axios/GalaxyApi before sending the
    // login POST — otherwise a late anonymous-cookie response can overwrite
    // the authenticated cookie we're about to receive.
    discardActiveConnectionsBeforeAuthNavigation();

    try {
        const response = await axios.post(
            withPrefix("/user/login"),
            {
                login: login.value,
                password: password.value,
                redirect: redirect,
                session_csrf_token: props.sessionCsrfToken,
            },
            { headers: { [SKIP_PENDING_REQUESTS_HEADER]: "1" } },
        );

        if (response.data.message && response.data.status) {
            alert(response.data.message);
        }

        if (response.data.expired_user) {
            await router.push({
                path: "/login/start",
                query: { expired_user: response.data.expired_user },
            });
        } else if (connectExternalProvider.value) {
            window.location.href = withPrefix("/user/external_ids?connect_external=true");
        } else if (response.data.redirect) {
            window.location.href = withPrefix(response.data.redirect);
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

function returnToLogin() {
    router.push("/login/start");
}

function goToResetPassword() {
    router.push({ path: "/login/reset_password", query: { email: login.value } });
}
</script>

<template>
    <div ref="loginFormRoot" class="login-form" :class="{ 'login-form-welcome': showWelcome }">
        <div class="d-flex justify-content-md-center" :class="{ 'flex-wrap justify-content-center': isNarrow }">
            <template v-if="!confirmURL">
                <div :class="{ 'login-column': showWelcome }">
                    <GAlert :show="!!messageText" :variant="messageVariant">
                        <span v-sanitize-html="messageText" />
                    </GAlert>

                    <GAlert :show="!!connectExternalProvider" variant="info">
                        There already exists a user with the email <i>{{ connectExternalEmail }}</i
                        >. In order to associate this account with <i>{{ connectExternalLabel }}</i
                        >, you must first login to your existing account.
                    </GAlert>

                    <div>
                        <BCard
                            no-body
                            style="width: fit-content"
                            :class="{ 'login-card-narrow': disableLocalAccounts || loginColumnDisplay }">
                            <BCardHeader v-if="!connectExternalProvider">
                                <span>{{ localize("Welcome to Galaxy, please log in") }}</span>
                            </BCardHeader>

                            <BCardBody :class="{ 'd-flex w-100': !loginColumnDisplay }">
                                <BForm
                                    v-if="!disableLocalAccounts"
                                    id="login"
                                    :class="{ 'login-local-row': !loginColumnDisplay }"
                                    @submit.prevent="submitLogin()">
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

                                        <BFormText v-if="showResetLink">
                                            <span v-localize>Forgot password?</span>

                                            <GLink
                                                id="reset-password-link"
                                                class="text-left"
                                                thin
                                                type="button"
                                                @click="goToResetPassword">
                                                <span v-localize>Click here to reset your password.</span>
                                            </GLink>
                                        </BFormText>
                                    </BFormGroup>

                                    <GButton
                                        name="login"
                                        type="submit"
                                        :disabled="loading"
                                        inline
                                        class="w-100 mt-1 py-1">
                                        {{ localize("Login") }}
                                    </GButton>
                                </BForm>

                                <template v-if="enableOidc">
                                    <VerticalSeparator v-if="!loginColumnDisplay && !disableLocalAccounts">
                                        <span v-localize>or</span>
                                    </VerticalSeparator>

                                    <hr v-else-if="!disableLocalAccounts" class="w-100" />

                                    <div class="m-1" :class="{ 'w-100': loginColumnDisplay || disableLocalAccounts }">
                                        <!-- OIDC login-->
                                        <ExternalLogin
                                            login-page
                                            :exclude-idps="excludeIdps"
                                            :column-display="loginColumnDisplay || disableLocalAccounts"
                                            :disable-local-accounts="disableLocalAccounts" />
                                    </div>
                                </template>
                            </BCardBody>

                            <BCardFooter class="login-footer">
                                <span v-if="!connectExternalProvider">
                                    Don't have an account?
                                    <GLink
                                        v-if="allowUserCreation && !disableLocalAccounts"
                                        id="register-toggle"
                                        to="/register/start">
                                        Register here.
                                    </GLink>
                                    <span v-else data-description="registration disabled message">
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
                    </div>
                </div>
            </template>
            <template v-else>
                <NewUserConfirmation
                    :session-csrf-token="sessionCsrfToken"
                    :registration-warning-message="registrationWarningMessage"
                    :terms-url="termsUrl"
                    @setRedirect="setRedirect" />
            </template>

            <div v-if="showWelcome && props.welcomeUrl" class="w-100">
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
    margin: 0 1rem;
    @media (min-width: 1200px) {
        margin: 0 10rem;
    }
}
.login-form-welcome {
    margin: 0 2rem;
    > div {
        gap: 2rem;
    }
}
.login-local-row {
    flex: 0 1 auto;
    min-width: 16rem;
}
.login-column {
    flex-shrink: 0;
    max-width: min(24rem, 100vw - 4rem);
}
/* Footer wraps to the body's width instead of widening the card. */
.login-footer {
    width: 0;
    min-width: 100%;
}
.login-card-narrow {
    max-width: min(22rem, 100vw - 2rem);
}
</style>
