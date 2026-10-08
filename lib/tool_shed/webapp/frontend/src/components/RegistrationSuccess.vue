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
            <p v-if="activationError" class="registration-message">
                There was an error sending you an activation e-mail, please contact {{ route.query.contact_email }} to
                this.
            </p>
            <p class="registration-message">Created new user account. Login in with your credentials as {{ email }}.</p>
            <login-form :initial-login="email" />
        </div>
    </ModalForm>
</template>

<style scoped>
.registration-message {
    margin: 0 0 1rem;
}
</style>
