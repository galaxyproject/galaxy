<script setup lang="ts">
import ModalForm from "@/components/ModalForm.vue"
import LoginForm from "@/components/LoginForm.vue"
</script>

<template>
    <ModalForm title="Login">
        <q-card-section>
            <login-form />
        </q-card-section>
        <q-card-section class="text-center q-pa-none">
            <p class="text-grey-6">
                Not registered? <router-link to="/register" class="register-link">Create an account</router-link>.
            </p>
        </q-card-section>
    </ModalForm>
</template>
