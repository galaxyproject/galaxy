<script setup lang="ts">
import axios from "axios";
import { BAlert, BCard, BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";

const router = useRouter();

const loading = ref(false);
const email = ref(router.currentRoute.query.email || "");
const message = ref("");
const messageVariant = ref("info");

async function resetLogin() {
    loading.value = true;
    try {
        const response = await axios.post(withPrefix("/user/reset_password"), { email: email.value });
        messageVariant.value = "info";
        message.value = response.data.message;
    } catch (e) {
        messageVariant.value = "danger";
        message.value = errorMessageAsString(e, "Password reset failed for an unknown reason.");
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="overflow-auto m-3">
        <div class="container">
            <div class="row justify-content-md-center">
                <div class="col col-lg-6">
                    <BForm @submit.prevent="resetLogin">
                        <BAlert v-if="!!message" id="reset-password-alert" class="mt-2" :variant="messageVariant" show>
                            {{ message }}
                        </BAlert>

                        <BCard header="Reset your password">
                            <BFormGroup label="Email Address">
                                <BFormInput id="reset-email" v-model="email" type="email" name="email" required />
                            </BFormGroup>

                            <GButton id="reset-password" v-localize type="submit" :disabled="loading">
                                Send password reset email
                            </GButton>
                        </BCard>
                    </BForm>
                </div>
            </div>
        </div>
    </div>
</template>
