<script setup lang="ts">
import axios from "axios";
import {
    BAlert,
    BButton,
    BCard,
    BCardBody,
    BCardFooter,
    BCardHeader,
    BCollapse,
    BForm,
    BFormCheckbox,
    BFormGroup,
    BFormInput,
    BFormText,
} from "bootstrap-vue";
import { computed, type Ref, ref } from "vue";

import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import ExternalLogin from "@/components/User/ExternalIdentities/ExternalLogin.vue";

interface Props {
    sessionCsrfToken: string;
    redirect?: string;
    termsUrl?: string;
    enableOidc?: boolean;
    showLoginLink?: boolean;
    mailingJoinAddr?: string;
    preferCustosLogin?: boolean;
    serverMailConfigured?: boolean;
    registrationWarningMessage?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "toggle-login"): void;
}>();

const email = ref(null);
const confirm = ref(null);
const password = ref(null);
const username = ref(null);
const subscribe = ref(null);
const messageText: Ref<string | null> = ref(null);
const disableCreate = ref(false);
const labelPassword = ref(localize("密码"));
const labelPublicName = ref(localize("公开名称"));
const labelEmailAddress = ref(localize("邮箱地址"));
const labelConfirmPassword = ref(localize("确认密码"));
const labelSubscribe = ref(localize("加入 galaxy-announce 邮件列表以获取最新资讯。"));

const custosPreferred = computed(() => {
    return props.enableOidc && props.preferCustosLogin;
});

function toggleLogin() {
    emit("toggle-login");
}

async function submit() {
    disableCreate.value = true;

    try {
        const response = await axios.post(withPrefix("/user/create"), {
            email: email.value,
            username: username.value,
            password: password.value,
            confirm: confirm.value,
            subscribe: subscribe.value,
            session_csrf_token: props.sessionCsrfToken,
        });

        if (response.data.message && response.data.status) {
            Toast.info(response.data.message);
        }

        window.location.href = props.redirect ? withPrefix(props.redirect) : withPrefix("/");
    } catch (error: any) {
        disableCreate.value = false;
        messageText.value = errorMessageAsString(error, "由于未知原因，注册失败。");
    }
}
</script>

<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col col-lg-6">
                <BAlert :show="!!registrationWarningMessage" variant="info">
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <span v-html="registrationWarningMessage" />
                </BAlert>

                <BAlert :show="!!messageText" variant="danger">
                    {{ messageText }}
                </BAlert>

                <BForm id="registration" @submit.prevent="submit()">
                    <BCard no-body>
                        <!-- OIDC and Custos enabled and prioritized: encourage users to use it instead of local registration -->
                        <span v-if="custosPreferred">
                            <BCardHeader v-b-toggle.accordion-oidc role="button">
                                使用机构账户注册
                            </BCardHeader>

                            <BCollapse id="accordion-oidc" visible role="tabpanel" accordion="registration_acc">
                                <BCardBody>
                                    使用机构账户（例如：Google/JHU）创建Galaxy账户。这将通过Custos将您重定向到您的机构登录页面。
                                    <ExternalLogin />
                                </BCardBody>
                            </BCollapse>
                        </span>

                        <!-- Local Galaxy Registration -->
                        <BCardHeader v-if="!custosPreferred" v-localize>创建Galaxy账户</BCardHeader>
                        <BCardHeader v-else v-localize v-b-toggle.accordion-register role="button">
                            或者，使用邮箱注册
                        </BCardHeader>

                        <BCollapse
                            id="accordion-register"
                            :visible="!custosPreferred"
                            role="tabpanel"
                            accordion="registration_acc">
                            <BCardBody>
                                <BFormGroup :label="labelEmailAddress" label-for="register-form-email">
                                    <BFormInput
                                        id="register-form-email"
                                        v-model="email"
                                        name="email"
                                        type="text"
                                        required />
                                </BFormGroup>

                                <BFormGroup :label="labelPassword" label-for="register-form-password">
                                    <BFormInput
                                        id="register-form-password"
                                        v-model="password"
                                        name="password"
                                        type="password"
                                        autocomplete="new-password"
                                        required />
                                </BFormGroup>

                                <BFormGroup :label="labelConfirmPassword" label-for="register-form-confirm">
                                    <BFormInput
                                        id="register-form-confirm"
                                        v-model="confirm"
                                        name="confirm"
                                        type="password"
                                        autocomplete="new-password"
                                        required />
                                </BFormGroup>

                                <BFormGroup :label="labelPublicName" label-for="register-form-username">
                                    <BFormInput
                                        id="register-form-username"
                                        v-model="username"
                                        name="username"
                                        type="text"
                                        required />

                                    <BFormText v-localize>
                                        您的公开名称是一个标识符，将用于生成您公开分享信息的地址。公开名称必须至少包含三个字符，并且只能包含小写字母、数字、点、下划线和短横线('.', '_', '-')。
                                    </BFormText>
                                </BFormGroup>

                                <BFormGroup v-if="mailingJoinAddr && serverMailConfigured">
                                    <BFormCheckbox
                                        id="register-form-subscribe"
                                        v-model="subscribe"
                                        name="subscribe"
                                        type="checkbox">
                                        {{ labelSubscribe }}
                                    </BFormCheckbox>
                                    <BFormText v-localize>
                                        此列表用于发送重要的Galaxy更新和新闻简报。我们会精简内容，您每月大约只会收到2-3封电子邮件。
                                    </BFormText>
                                </BFormGroup>

                                <BButton v-localize name="create" type="submit" :disabled="disableCreate">
                                    创建
                                </BButton>
                            </BCardBody>
                        </BCollapse>

                        <BCardFooter v-if="showLoginLink">
                            <span v-localize>已有账户？</span>

                            <a
                                id="login-toggle"
                                v-localize
                                href="javascript:void(0)"
                                role="button"
                                @click.prevent="toggleLogin">
                                点此登录。
                            </a>
                        </BCardFooter>
                    </BCard>
                </BForm>
            </div>

            <div v-if="termsUrl" class="col position-relative embed-container">
                <iframe title="terms-of-use" :src="termsUrl" frameborder="0" class="terms-iframe"></iframe>
                <div v-localize class="scroll-hint">↓ 向下滚动以查看 ↓</div>
            </div>
        </div>
    </div>
</template>
<style scoped lang="scss">
.embed-container {
    position: relative;

    .terms-iframe {
        width: 100%;
        height: 90vh;
        border: none;
        overflow-y: auto;
    }

    .scroll-hint {
        position: absolute;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        background-color: rgba(255, 255, 255, 0.9);
        border: 1px solid #ccc;
        padding: 2px 5px;
        border-radius: 4px;
    }
}
</style>
