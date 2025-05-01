<script setup lang="ts">
import axios from "axios";
import {
    BAlert,
    BButton,
    BCard,
    BCardBody,
    BCardFooter,
    BEmbed,
    BForm,
    BFormCheckbox,
    BFormGroup,
} from "bootstrap-vue";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    termsUrl?: string;
    registrationWarningMessage?: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "setRedirect", value: string): void;
}>();

const router = useRouter();

const urlParams = new URLSearchParams(window.location.search);

const messageText = ref("");
const termsRead = ref(false);
const messageVariant = ref("");
const provider = ref(urlParams.get("provider"));
const token = ref(urlParams.get("provider_token"));

function login() {
    // set url to redirect user to 3rd party management after login
    emit("setRedirect", "/user/external_ids");
    router.push("/login");
}

async function submit() {
    if (!provider.value || !token.value) {
        messageVariant.value = "danger";
        messageText.value = "缺少提供商和/或令牌。";
    } else {
        try {
            const response = await axios.post(withPrefix(`/authnz/${provider.value}/create_user?token=${token.value}`));

            if (response.data.redirect_uri) {
                router.push(response.data.redirect_uri);
            } else {
                router.push("/");
            }
        } catch (error: any) {
            messageVariant.value = "danger";
            messageText.value = errorMessageAsString(error, "登录失败，原因未知。");
        }
    }
}
</script>

<template>
    <div class="container">
        <div class="row justify-content-md-center">
            <div class="col col-lg-6">
                <BAlert :show="!!registrationWarningMessage" variant="info">
                    {{ registrationWarningMessage }}
                </BAlert>

                <BAlert :show="!!messageText" :variant="messageVariant">
                    {{ messageText }}
                </BAlert>

                <BForm id="confirmation" @submit.prevent="submit()">
                    <BCard no-body header="确认创建新账户">
                        <BCardBody>
                            <p>看起来您即将创建一个新账户！</p>

                            <p>
                                您是否已经拥有Galaxy账户？如果有，请点击
                                <em>"否，返回登录页面"</em>使用您现有的用户名和密码登录，然后通过<strong>用户偏好设置</strong>关联此账户。
                                <a
                                    href="https://galaxyproject.org/authnz/use/oidc/idps/custos/#link-an-existing-galaxy-account"
                                    target="_blank">
                                    点此查看更多详情。
                                </a>
                            </p>

                            <p>
                                如果您希望继续并创建一个新账户，请选择
                                <em>"是，创建新账户"</em>。
                            </p>

                            <p>
                                提醒：公共Galaxy服务器会跟踪注册和使用多个账户的行为，此类账户可能会被终止并删除数据。现在关联现有账户以继续使用您的现有数据，避免可能的数据丢失。
                            </p>

                            <BFormGroup>
                                <BFormCheckbox v-model="termsRead">
                                    我已阅读并接受这些条款以创建新的Galaxy账户。
                                </BFormCheckbox>
                            </BFormGroup>

                            <BButton name="confirm" type="submit" :disabled="!termsRead" @click.prevent="submit">
                                是，创建新账户
                            </BButton>

                            <BButton name="cancel" type="submit" @click.prevent="login"> 否，返回登录页面 </BButton>
                        </BCardBody>

                        <BCardFooter>
                            已有账户？
                            <a id="login-toggle" href="javascript:void(0)" role="button" @click.prevent="login">
                                点此登录。
                            </a>
                        </BCardFooter>
                    </BCard>
                </BForm>
            </div>

            <div v-if="termsUrl" class="col">
                <BEmbed type="iframe" :src="withPrefix(termsUrl)" aspect="1by1" />
            </div>
        </div>
    </div>
</template>
