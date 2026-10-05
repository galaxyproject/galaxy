<script setup lang="ts">
import ModalForm from "@/components/ModalForm.vue"
import LoginForm from "@/components/LoginForm.vue"
import { queryParamToString } from "@/util"
import { useRoute } from "vue-router"
const route = useRoute()
const activationError = route.query.activation_error == "true"
const email = queryParamToString(route.query.email)
</script>

<template>
    <ModalForm title="Registration Successful">
        <div class="modal-form-section">
            <div v-if="activationError">
                There was an error sending you an activation e-mail, please contact {{ route.query.contact_email }} to
                this.
            </div>
            Created new user account. Login in with your credentials as {{ email }}.
            <login-form :initial-login="email" />
        </div>
    </ModalForm>
</template>

<style scoped>
.modal-form-section {
    padding: var(--spacing-4);
}
</style>
