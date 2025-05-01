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
    } catch (e) {
        loading.value = false;
        messageVariant.value = "danger";
        const message = errorMessageAsString(e, "登录失败，原因未知。");

        if (connectExternalProvider.value && message && message.toLowerCase().includes("invalid")) {
            messageText.value = message + " 尝试通过以下外部提供商登录到现有帐户。";
        } else {
            messageText.value = message;
        }
        if (message === "密码无效。") {
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
    <div class="container">
        <div class="row justify-content-md-center">
            <template v-if="!confirmURL">
                <div class="col col-lg-6">
                    <BAlert :show="!!messageText" :variant="messageVariant">
                        <!-- eslint-disable-next-line vue/no-v-html -->
                        <span v-html="messageText" />
                    </BAlert>

                    <BAlert :show="!!connectExternalProvider" variant="info">
                        已存在一个使用邮箱 <i>{{ connectExternalEmail }}</i> 的用户。为了将此账户与 <i>{{ connectExternalLabel }}</i> 关联，您必须先登录到您的现有账户。
                    </BAlert>

                    <BForm id="login" @submit.prevent="submitLogin()">
                        <BCard no-body>
                            <BCardHeader v-if="!connectExternalProvider">
                                <span>{{ localize("欢迎使用Galaxy，请登录") }}</span>
                            </BCardHeader>

                            <BCardBody>
                                <div>
                                    <!-- standard internal galaxy login -->
                                    <BFormGroup
                                        :label="localize('用户名或电子邮箱')"
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

                                    <BFormGroup :label="localize('密码')" label-for="login-form-password">
                                        <BFormInput
                                            id="login-form-password"
                                            v-model="password"
                                            required
                                            :state="passwordState"
                                            name="password"
                                            type="password"
                                            autocomplete="current-password" />

                                        <BFormText v-if="showResetLink">
                                            <span v-localize>忘记密码？</span>

                                            <a
                                                v-localize
                                                href="javascript:void(0)"
                                                role="button"
                                                @click.prevent="resetLogin">
                                                点击此处重置您的密码。
                                            </a>
                                        </BFormText>
                                    </BFormGroup>

                                    <BButton v-localize name="login" type="submit" :disabled="loading">
                                        {{ localize("登录") }}
                                    </BButton>
                                </div>
                                <div v-if="enableOidc">
                                    <!-- OIDC login-->
                                    <ExternalLogin login-page :exclude-idps="excludeIdps" />
                                </div>
                            </BCardBody>

                            <BCardFooter>
                                <span v-if="!connectExternalProvider">
                                    没有账户？
                                    <span v-if="allowUserCreation">
                                        <a
                                            id="register-toggle"
                                            v-localize
                                            href="javascript:void(0)"
                                            role="button"
                                            @click.prevent="toggleLogin">
                                            在此注册。
                                        </a>
                                    </span>
                                    <span v-else>
                                        此Galaxy实例的注册功能已禁用。请联系管理员获取帮助。
                                    </span>
                                </span>
                                <span v-else>
                                    不想连接到外部提供商？
                                    <a href="javascript:void(0)" role="button" @click.prevent="returnToLogin">
                                        点此返回登录。
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
