<script setup lang="ts">
import { ref } from "vue"
import ModalForm from "@/components/ModalForm.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import { AUTH_FORM_INPUT_PROPS } from "@/constants"
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
            <q-form v-else name="forgot_password" class="q-gutter-md" action="#" @submit.prevent="onSubmit">
                <p class="text-grey-8">
                    Enter the email address of your account and we will send you a link to choose a new password.
                </p>
                <q-input v-bind="AUTH_FORM_INPUT_PROPS" v-model="email" type="email" label="E-Mail" name="email" />
                <q-btn
                    unelevated
                    color="primary"
                    size="lg"
                    class="full-width"
                    label="Send Reset Link"
                    type="submit"
                    name="reset_password_button"
                />
            </q-form>
        </q-card-section>
        <q-card-section class="text-center q-pa-none">
            <p class="text-grey-6">Remembered it? <router-link to="/login">Login.</router-link></p>
        </q-card-section>
    </modal-form>
</template>
