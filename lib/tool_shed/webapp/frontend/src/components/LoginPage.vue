<script setup lang="ts">
import ModalForm from "@/components/ModalForm.vue"
import LoginForm from "@/components/LoginForm.vue"
</script>

<template>
    <ModalForm title="Login">
        <div class="modal-form-section">
            <login-form />
        </div>
        <div class="modal-form-section modal-form-section-footer">
            <p class="modal-form-footer-text">
                Not registered? <router-link to="/register" class="register-link">Create an account</router-link>.
            </p>
            <p class="modal-form-footer-text">
                <router-link to="/user/forgot_password" class="forgot-password-link">Forgot your password?</router-link>
            </p>
        </div>
    </ModalForm>
</template>
