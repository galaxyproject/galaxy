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
        <div class="modal-form-section">
            <error-banner v-if="error" :error="error" @dismiss="dismiss" />
            <p v-if="sent" class="reset-password-sent">
                If an account exists for that address, a password reset link is on its way. The link expires in 24
                hours.
            </p>
            <GForm v-else name="forgot_password" class="forgot-password-form" action="#" @submit.prevent="onSubmit">
                <p class="forgot-password-intro">
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
                <GButton color="blue" size="large" class="submit-button" type="submit" name="reset_password_button"
                    >Send Reset Link</GButton
                >
            </GForm>
        </div>
        <div class="modal-form-section modal-form-section-footer">
            <p class="modal-form-footer-text">Remembered it? <router-link to="/login">Login.</router-link></p>
        </div>
    </modal-form>
</template>

<style scoped>
.forgot-password-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
}

.submit-button {
    width: 100%;
}

.forgot-password-intro {
    color: var(--color-grey-800);
}

.modal-form-section {
    padding: var(--spacing-4);
}

.modal-form-section-footer {
    padding: 0;
    text-align: center;
}

.modal-form-footer-text {
    color: var(--color-grey-600);
}
</style>
