<script setup lang="ts">
import { GButton, GForm, GFormInput, GFormLabel } from "@galaxyproject/galaxy-ui"
import { ref } from "vue"
import ModalForm from "@/components/ModalForm.vue"
import { ToolShedApi } from "@/schema"
import { notifyOnCatch } from "@/util"
import router from "@/router"

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
        <div class="modal-form-section">
            <GForm name="registration" class="registration-form" action="#" @submit.prevent="onRegister">
                <GFormLabel title="E-Mail">
                    <GFormInput
                        :model-value="email"
                        type="email"
                        name="email"
                        autocomplete="email"
                        @update:model-value="email = $event ?? ''"
                    />
                </GFormLabel>
                <GFormLabel title="Password">
                    <GFormInput
                        :model-value="password"
                        type="password"
                        name="password"
                        autocomplete="new-password"
                        @update:model-value="password = $event ?? ''"
                    />
                </GFormLabel>
                <GFormLabel title="Re-enter Password">
                    <GFormInput
                        :model-value="confirm"
                        type="password"
                        name="confirm"
                        autocomplete="new-password"
                        @update:model-value="confirm = $event ?? ''"
                    />
                </GFormLabel>
                <GFormLabel title="Username">
                    <GFormInput
                        :model-value="username"
                        type="text"
                        name="username"
                        autocomplete="username"
                        @update:model-value="username = $event ?? ''"
                    />
                </GFormLabel>
                <GButton color="blue" size="large" class="full-width" type="submit" name="create_user_button">
                    Register
                </GButton>
            </GForm>
        </div>
        <div class="modal-form-section modal-form-section-footer">
            <p class="modal-form-footer-text">Already registered? <router-link to="/login">Login.</router-link></p>
        </div>
    </ModalForm>
</template>

<style scoped>
.registration-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-4);
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
