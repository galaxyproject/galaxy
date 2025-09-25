<script setup lang="ts">
import axios from "axios";
import {
    BAlert,
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

import { getOIDCIdpsWithRegistration, type OIDCConfig } from "@/components/User/ExternalIdentities/ExternalIDHelper";
import { Toast } from "@/composables/toast";
import localize from "@/utils/localization";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "../BaseComponents/GButton.vue";
import GLink from "../BaseComponents/GLink.vue";
import VerticalSeparator from "../Common/VerticalSeparator.vue";
import ExternalLogin from "@/components/User/ExternalIdentities/ExternalLogin.vue";
import ExternalRegistration from "@/components/User/ExternalIdentities/ExternalRegistration.vue";

interface Props {
    disableLocalAccounts?: boolean;
    enableOidc?: boolean;
    mailingJoinAddr?: string;
    oidcIdps?: OIDCConfig;
    preferCustosLogin?: boolean;
    redirect?: string;
    registrationWarningMessage?: string;
    serverMailConfigured?: boolean;
    sessionCsrfToken: string;
    hideLoginLink?: boolean; // TODO: Configure this properly
    termsUrl?: string;
}

const props = defineProps<Props>();

const email = ref(null);
const confirm = ref(null);
const password = ref(null);
const username = ref(null);
const subscribe = ref(null);
const messageText: Ref<string | null> = ref(null);
const disableCreate = ref(false);
const labelPassword = ref(localize("Password"));
const labelPublicName = ref(localize("Public name"));
const labelEmailAddress = ref(localize("Email address"));
const labelConfirmPassword = ref(localize("Confirm password"));
const labelSubscribe = ref(localize("Stay in the loop and join the galaxy-announce mailing list."));

const idpsWithRegistration = computed(() => (props.oidcIdps ? getOIDCIdpsWithRegistration(props.oidcIdps) : {}));

const custosPreferred = computed(() => {
    return props.enableOidc && props.preferCustosLogin;
});

/** This decides if all register options should be displayed in column style
 * (one below the other) or horizontally.
 */
const registerColumnDisplay = computed(() => Boolean(props.termsUrl));

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
    <div class="register-form">
        <div class="d-flex justify-content-md-center">
            <div>
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
                                    <ExternalLogin class="mt-2" />
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
                            <BCardBody :class="{ 'd-flex w-100': !registerColumnDisplay }">
                                <div v-if="!disableLocalAccounts">
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
                                            Your public name is an identifier that will be used to generate addresses
                                            for information you share publicly. Public names must be at least three
                                            characters in length and contain only lower-case letters, numbers, dots,
                                            underscores, and dashes ('.', '_', '-').
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
                                            This list is used for important Galaxy updates and newsletter access. We
                                            keep it streamlined, you should expect only 2-3 emails per month.
                                        </BFormText>
                                    </BFormGroup>

                                    <GButton v-localize name="create" type="submit" :disabled="disableCreate">
                                        Create
                                    </GButton>
                                </div>

                                <template v-if="Object.keys(idpsWithRegistration).length > 0">
                                    <VerticalSeparator v-if="!registerColumnDisplay && !disableLocalAccounts">
                                        <span v-localize>or</span>
                                    </VerticalSeparator>

                                    <hr v-else-if="!disableLocalAccounts" class="w-100" />

                                    <div class="m-1 w-100">
                                        <ExternalRegistration
                                            :idps-with-registration="idpsWithRegistration"
                                            :column-display="registerColumnDisplay" />
                                    </div>
                                </template>
                            </BCardBody>
                        </BCollapse>

                        <BCardFooter v-if="!hideLoginLink">
                            <span v-localize>Already have an account?</span>

                            <GLink id="login-toggle" to="/login/start"> Log in here. </GLink>
                        </BCardFooter>
                    </BCard>
                </BForm>
            </div>

            <div v-if="termsUrl" class="w-100 position-relative embed-container">
                <iframe title="terms-of-use" :src="termsUrl" frameborder="0" class="terms-iframe"></iframe>
                <div v-localize class="scroll-hint">↓ Scroll to review ↓</div>
            </div>
        </div>
    </div>
</template>
<style scoped lang="scss">
.register-form {
    margin: 0rem 10rem;
}
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
