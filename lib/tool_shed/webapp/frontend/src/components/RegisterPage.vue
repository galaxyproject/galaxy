<script setup lang="ts">
import { ref } from "vue"
import ModalForm from "@/components/ModalForm.vue"
import { ToolShedApi } from "@/schema"
import { notifyOnCatch } from "@/util"
import router from "@/router"
import { AUTH_FORM_INPUT_PROPS } from "@/constants"

const email = ref("")
const password = ref("")
const confirm = ref("")
const username = ref("")

const title = ref("Register")
// type Response = components["schemas"]["UiRegisterResponse"]

async function onRegister() {
    // TODO: handle confirm and implement bear_field.
    // let data: Response
    try {
        const { data } = await ToolShedApi().POST("/api_internal/register", {
            body: {
                email: email.value,
                password: password.value,
                username: username.value,
                bear_field: "",
            },
        })

        if (!data) {
            return
        }

        const query = {
            activation_error: data.activation_error ? "true" : "false",
            activation_sent: data.activation_sent ? "true" : "false",
            contact_email: data.contact_email,
            email: data.email,
        }
        router.push({ path: "/registration_success", query: query })
    } catch (e) {
        notifyOnCatch(e)
    }
}
</script>

<template>
    <ModalForm :title="title">
        <q-card-section>
            <q-form name="registration" class="q-gutter-md" action="#" @submit.prevent="onRegister">
                <q-input v-bind="AUTH_FORM_INPUT_PROPS" v-model="email" type="email" label="E-Mail" name="email" />
                <q-input
                    v-bind="AUTH_FORM_INPUT_PROPS"
                    v-model="password"
                    type="password"
                    label="Password"
                    name="password"
                />
                <q-input
                    v-bind="AUTH_FORM_INPUT_PROPS"
                    v-model="confirm"
                    type="password"
                    label="Re-enter Password"
                    name="confirm"
                />
                <q-input
                    v-bind="AUTH_FORM_INPUT_PROPS"
                    v-model="username"
                    type="text"
                    label="Username"
                    name="username"
                />
                <q-btn
                    unelevated
                    color="primary"
                    size="lg"
                    class="full-width"
                    label="Register"
                    type="submit"
                    name="create_user_button"
                />
            </q-form>
        </q-card-section>
        <q-card-section class="text-center q-pa-none">
            <p class="text-grey-6">Already registered? <router-link to="/login">Login.</router-link></p>
        </q-card-section>
    </ModalForm>
</template>
