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
    BModal,
} from "bootstrap-vue";
import { computed, type Ref, ref } from "vue";

import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import ExternalLogin from "@/components/User/ExternalIdentities/ExternalLogin.vue";
import PasswordStrength from "@/components/Login/PasswordStength.vue";

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
const password = ref<string | null>(null);
const username = ref(null);
const subscribe = ref(null);
const messageText: Ref<string | null> = ref(null);
const disableCreate = ref(false);
const labelPassword = ref(localize("Password"));
const labelPublicName = ref(localize("Public name"));
const labelEmailAddress = ref(localize("Email address"));
const labelConfirmPassword = ref(localize("Confirm password"));
const labelSubscribe = ref(localize("Stay in the loop and join the galaxy-announce mailing list."));

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
        messageText.value = errorMessageAsString(error, "Registration failed for an unknown reason.");
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
                                Register using institutional account
                            </BCardHeader>

                            <BCollapse id="accordion-oidc" visible role="tabpanel" accordion="registration_acc">
                                <BCardBody>
                                    Create a Galaxy account using an institutional account (e.g.:Google/JHU). This will
                                    redirect you to your institutional login through Custos.
                                    <ExternalLogin />
                                </BCardBody>
                            </BCollapse>
                        </span>

                        <!-- Local Galaxy Registration -->
                        <BCardHeader v-if="!custosPreferred" v-localize>Create a Galaxy account</BCardHeader>
                        <BCardHeader v-else v-localize v-b-toggle.accordion-register role="button">
                            Or, register with email
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
                                        required 
                                    />
                                    <!-- Password Strength Component -->
                                    <PasswordStrength :password="password" />
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
                                        Your public name is an identifier that will be used to generate addresses for
                                        information you share publicly. Public names must be at least three characters
                                        in length and contain only lower-case letters, numbers, dots, underscores, and
                                        dashes ('.', '_', '-').
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
                                        This list is used for important Galaxy updates and newsletter access. We keep it
                                        streamlined, you should expect only 2-3 emails per month.
                                    </BFormText>
                                </BFormGroup>

                                <BButton v-localize name="create" type="submit" :disabled="disableCreate">
                                    Create
                                </BButton>
                            </BCardBody>
                        </BCollapse>

                        <BCardFooter v-if="showLoginLink">
                            <span v-localize>Already have an account?</span>

                            <a
                                id="login-toggle"
                                v-localize
                                href="javascript:void(0)"
                                role="button"
                                @click.prevent="toggleLogin">
                                Log in here.
                            </a>
                        </BCardFooter>
                    </BCard>
                </BForm>
            </div>

            <div v-if="termsUrl" class="col position-relative embed-container">
                <iframe title="terms-of-use" :src="termsUrl" frameborder="0" class="terms-iframe"></iframe>
                <div v-localize class="scroll-hint">↓ Scroll to review ↓</div>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

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
