<script setup lang="ts">
import { GButton, GForm, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { ref } from "vue"
import ModalForm from "@/components/ModalForm.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import { ToolShedApi } from "@/schema"
import { errorMessageAsString } from "@/util"

const email = ref("")
const error = ref<string | null>(null)
const sent = ref(false)

async function onSubmit() {
    error.value = null
    try {
        await ToolShedApi().POST("/api_internal/reset_password", {
            body: {
                email: email.value,
                bear_field: "",
            },
        })
        sent.value = true
    } catch (e) {
        error.value = errorMessageAsString(e)
    }
}

function dismiss() {
    error.value = null
}
</script>

<template>
    <modal-form title="Forgot Password">
        <q-card-section>
            <error-banner v-if="error" :error="error" @dismiss="dismiss" />
            <p v-if="sent" class="text-body1 reset-password-sent">
                If an account exists for that address, a password reset link is on its way. The link expires in 24
                hours.
            </p>
            <GForm v-else name="forgot_password" class="forgot-password-form" action="#" @submit.prevent="onSubmit">
                <p class="text-grey-8">
                    Enter the email address of your account and we will send you a link to choose a new password.
                </p>
                <GFormLabel title="E-Mail">
                    <GFormInput
                        :model-value="email"
                        type="email"
                        name="email"
                        autocomplete="email"
                        @update:model-value="email = $event ?? ''"
                    />
                </GFormLabel>
                <GButton color="blue" size="large" class="full-width" type="submit" name="reset_password_button"
                    >Send Reset Link</GButton
                >
            </GForm>
        </q-card-section>
        <q-card-section class="text-center q-pa-none">
            <p class="text-grey-6">Remembered it? <router-link to="/login">Login.</router-link></p>
        </q-card-section>
    </modal-form>
</template>

<style scoped>
.forgot-password-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
}
</style>
