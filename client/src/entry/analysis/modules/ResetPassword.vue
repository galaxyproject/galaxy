<script setup lang="ts">
import axios from "axios";
import { BAlert, BButton, BCard, BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { ref } from "vue";

import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

const loading = ref(false);
const email = ref("");
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
    <div class="container">
        <div class="justify-content-md-center">
            <BForm @submit.prevent="resetLogin">
                <BAlert v-if="!!message" class="mt-2" :variant="messageVariant" show>
                    {{ message }}
                </BAlert>

                <BCard header="Reset your password">
                    <BFormGroup label="Email Address">
                        <BFormInput id="reset-email" v-model="email" type="email" />
                    </BFormGroup>

                    <BButton type="submit">Reset your password</BButton>
                </BCard>
            </BForm>
        </div>
    </div>
</template>
