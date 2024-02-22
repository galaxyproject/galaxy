<script setup lang="ts">
import axios from "axios";
import { capitalize } from "lodash";
import { computed, ref } from "vue";
import { useRoute } from "vue-router/composables";

import { useConfig } from "@/composables/config";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";

import Heading from "../Common/Heading.vue";
import InternalLogin from "./InternalLogin.vue";
import NewUserConfirmation from "./NewUserConfirmation.vue";
import ExternalLogin from "@/components/User/ExternalIdentities/ExternalLogin.vue";

interface Props {
    allowUserCreation: boolean;
    enableOidc: boolean;
    redirect: string;
    registrationWarningMessage: string;
    sessionCsrfToken: string;
    showAsBox: boolean;
    showWelcomeWithLogin: boolean;
    termsUrl: string;
    welcomeUrl: string;
}

const props = withDefaults(defineProps<Props>(), {
    allowUserCreation: false,
    enableOidc: false,
    showAsBox: false,
    showWelcomeWithLogin: false,
});

const emit = defineEmits<{
    (e: "toggle-login"): void;
}>();

const urlParams = new URLSearchParams(window.location.search);

const { config } = useConfig();
const route = useRoute();

const login = ref<string | null>(null);
const password = ref<string | null>(null);
const passwordState = ref<boolean | null>(null);
const messageText = ref<string | null>(null);
const messageVariant = ref<string | null>(null);
const headerWelcome = ref<string>(
    localize(props.showAsBox ? "Please log in to Galaxy" : "Welcome to Galaxy, please log in")
);

const confirmURL = ref<boolean>(urlParams.has("confirm") && urlParams.get("confirm") == "true");
const connectExternalEmail = ref<string | null>(urlParams.get("connect_external_email"));
const connectExternalProvider = ref<string | null>(urlParams.get("connect_external_provider"));
const connectExternalLabel = ref<string | null>(urlParams.get("connect_external_label"));

const boxSection = ref<number>(1);
const boxSections = computed(() => {
    const sections = ["galaxy"]; // TODO: what if localdb is disabled
    if (config.value?.enable_oidc && config.value?.oidc) {
        sections.push(...Object.keys(config.value.oidc));
    }
    return sections;
});
const totalSections = computed(() => boxSections.value.length);

const welcomeUrlWithRoot = computed(() => {
    return withPrefix(props.welcomeUrl);
});

function toggleLogin() {
    emit("toggle-login");
}

function submitLogin(formLogin: string | null, formPassword: string | null) {
    login.value = formLogin;
    password.value = formPassword;
    passwordState.value = null;
    let redirect = props.redirect;
    if (connectExternalEmail.value) {
        login.value = connectExternalEmail.value;
    }
    if (localStorage.getItem("redirect_url")) {
        redirect = localStorage.getItem("redirect_url")!;
    }
    const currentPath = route.fullPath;
    axios
        .post(withPrefix("/user/login"), {
            login: login.value,
            password: password.value,
            redirect: redirect,
            session_csrf_token: props.sessionCsrfToken,
        })
        .then(({ data }) => {
            let location;
            if (data.message && data.status) {
                alert(data.message);
            }
            if (data.expired_user) {
                location = withPrefix(`/root/login?expired_user=${data.expired_user}`);
            } else if (connectExternalProvider.value) {
                location = withPrefix("/user/external_ids?connect_external=true");
            } else if (data.redirect) {
                location = encodeURI(data.redirect);
            } else if (props.showAsBox) {
                location = withPrefix(currentPath);
            } else {
                location = withPrefix("/");
            }
            window.location = location as string & Location;
        })
        .catch((error) => {
            messageVariant.value = "danger";
            const message = error.response && error.response.data && error.response.data.err_msg;
            if (connectExternalProvider.value && message && message.toLowerCase().includes("invalid")) {
                messageText.value =
                    message + " Try logging in to the existing account through an external provider below.";
            } else {
                messageText.value = message || "Login failed for an unknown reason.";
            }
            if (messageText.value && props.showAsBox) {
                Toast.error(messageText.value);
            }
            if (message === "Invalid password.") {
                passwordState.value = false;
            }
        });
}

function setRedirect(url: string) {
    localStorage.setItem("redirect_url", url);
}

function resetLogin(formLogin: string | null) {
    login.value = formLogin;
    axios
        .post(withPrefix("/user/reset_password"), { email: login.value })
        .then((response) => {
            messageVariant.value = "info";
            messageText.value = response.data.message;
        })
        .catch((error) => {
            messageVariant.value = "danger";
            const message = error.response.data && error.response.data.err_msg;
            messageText.value = message || "Password reset failed for an unknown reason.";
        });
}

function returnToLogin() {
    window.location = withPrefix("/login/start") as string & Location;
}
</script>

<template>
    <div :class="{ container: !showAsBox }">
        <div :class="!showAsBox ? 'row justify-content-md-center' : ''">
            <template v-if="!confirmURL">
                <div v-if="!showAsBox" class="col col-lg-6">
                    <b-alert :show="!!messageText" :variant="messageVariant">
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <span v-html="messageText" />
                    </b-alert>
                    <b-alert :show="!!connectExternalProvider" variant="info">
                        There already exists a user with the email <i>{{ connectExternalEmail }}</i
                        >. In order to associate this account with <i>{{ connectExternalLabel }}</i
                        >, you must first login to your existing account.
                    </b-alert>
                    <b-card no-body>
                        <b-card-header v-if="!connectExternalProvider">
                            <span>{{ headerWelcome }}</span>
                        </b-card-header>
                        <b-card-body>
                            <div>
                                <!-- standard internal galaxy login -->
                                <InternalLogin
                                    :password-state="passwordState"
                                    :connect-external-provider="connectExternalProvider"
                                    :connect-external-email="connectExternalEmail"
                                    @reset-login="resetLogin"
                                    @submit-login="submitLogin" />
                            </div>
                            <div v-if="enableOidc">
                                <!-- OIDC login-->
                                <ExternalLogin :login_page="true" :exclude_idps="[connectExternalProvider]" />
                            </div>
                        </b-card-body>
                        <b-card-footer>
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
                                    Registration for this Galaxy instance is disabled. Please contact an administrator
                                    for assistance.
                                </span>
                            </span>
                            <span v-else>
                                Do not wish to connect to an external provider?
                                <a href="javascript:void(0)" role="button" @click.prevent="returnToLogin">
                                    Return to login here.
                                </a>
                            </span>
                        </b-card-footer>
                    </b-card>
                </div>
                <div v-else :class="{ 'd-flex': termsUrl }">
                    <div class="border p-3 login-box">
                        <div class="d-flex flex-column justify-content-center align-items-center h-100">
                            <div class="w-100">
                                <Heading h6 separator size="sm">{{ headerWelcome }}</Heading>
                                <span v-if="boxSection == 1">
                                    <InternalLogin
                                        show-as-box
                                        :password-state="passwordState"
                                        :connect-external-provider="connectExternalProvider"
                                        :connect-external-email="connectExternalEmail"
                                        @reset-login="resetLogin"
                                        @submit-login="submitLogin" />
                                </span>
                                <span v-else>
                                    <ExternalLogin
                                        :login_page="true"
                                        indexed-view
                                        :provider-key="boxSections[boxSection - 1]"
                                        :exclude_idps="[connectExternalProvider]" />
                                </span>
                            </div>
                            <div v-if="boxSections.length > 1" class="mt-auto text-center">
                                <i>Try other login options</i>
                                <b-pagination
                                    v-model="boxSection"
                                    align="center"
                                    hide-goto-end-buttons
                                    :per-page="1"
                                    :total-rows="totalSections"
                                    size="sm">
                                    <template v-slot:page="{ page, active }">
                                        <b v-if="active">{{ capitalize(boxSections[page - 1]) }}</b>
                                        <span v-else>{{ capitalize(boxSections[page - 1]) }}</span>
                                    </template>
                                </b-pagination>
                            </div>
                        </div>
                    </div>
                    <div v-if="termsUrl" class="border p-3 login-box right-terms">
                        <iframe title="terms-of-use" :src="termsUrl" frameborder="0" class="terms-iframe"></iframe>
                    </div>
                </div>
            </template>
            <template v-else>
                <NewUserConfirmation
                    :registration-warning-message="registrationWarningMessage"
                    :terms-url="termsUrl"
                    @setRedirect="setRedirect" />
            </template>
            <div v-if="showWelcomeWithLogin" class="col">
                <b-embed type="iframe" :src="welcomeUrlWithRoot" aspect="1by1" />
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
.card-body {
    overflow: visible;
}
.login-box {
    border-radius: 4px;
    &.right-terms {
        flex: 1;
    }

    &:not(.right-terms) {
        min-width: 30%;
    }

    .terms-iframe {
        border: none;
        overflow-y: auto;
        width: 100%;
        min-height: 10vh;
        height: 100%;
    }
}
</style>
