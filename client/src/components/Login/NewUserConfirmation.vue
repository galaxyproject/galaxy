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
        messageText.value = "Missing provider and/or token.";
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
            messageText.value = errorMessageAsString(error, "Login failed for an unknown reason.");
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
                    <BCard no-body header="Confirm new account creation">
                        <BCardBody>
                            <p>Looks like you are about to create a new account!</p>

                            <p>
                                Do you already have a Galaxy account? If so, click
                                <em>'No, go back to login'</em> to log in using your existing username and password to
                                connect this account via <strong>User Preferences</strong>.
                                <a
                                    href="https://galaxyproject.org/authnz/use/oidc/idps/custos/#link-an-existing-galaxy-account"
                                    target="_blank">
                                    More details here.
                                </a>
                            </p>

                            <p>
                                If you wish to continue and create a new account, select
                                <em>'Yes, create new account'</em>.
                            </p>

                            <p>
                                Reminder: Registration and usage of multiple accounts is tracked and such accounts are
                                subject to termination and data deletion on public Galaxy servers. Connect existing
                                account now to continue to use your existing data and avoid possible loss of data.
                            </p>

                            <BFormGroup>
                                <BFormCheckbox v-model="termsRead">
                                    I have read and accept these terms to create a new Galaxy account.
                                </BFormCheckbox>
                            </BFormGroup>

                            <BButton name="confirm" type="submit" :disabled="!termsRead" @click.prevent="submit">
                                Yes, create new account
                            </BButton>

                            <BButton name="cancel" type="submit" @click.prevent="login"> No, go back to login </BButton>
                        </BCardBody>

                        <BCardFooter>
                            Already have an account?
                            <a id="login-toggle" href="javascript:void(0)" role="button" @click.prevent="login">
                                Log in here.
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
