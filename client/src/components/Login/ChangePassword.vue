<script setup lang="ts">
import axios from "axios";
import { BAlert, BButton, BCard, BForm, BFormGroup, BFormInput } from "bootstrap-vue";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    token?: string;
    expiredUser?: string;
    messageText?: string;
    messageVariant?: string;
}

const props = defineProps<Props>();

const router = useRouter();

const confirm = ref(null);
const current = ref(null);
const password = ref(null);
const message = ref(props.messageText);
const variant = ref(props.messageVariant);

async function submit() {
    try {
        await axios.post(withPrefix("/user/change_password"), {
            token: props.token,
            id: props.expiredUser,
            current: current.value,
            password: password.value,
            confirm: confirm.value,
        });

        router.push("/");
    } catch (error: any) {
        variant.value = "danger";
        message.value = errorMessageAsString(error, "密码修改失败，原因未知。");
    }
}
</script>

<template>
    <BForm @submit.prevent="submit">
        <BAlert v-if="!!message" :variant="variant" show>
            {{ message }}
        </BAlert>

        <BCard header="修改密码">
            <BFormGroup v-if="expiredUser" label="当前密码">
                <BFormInput v-model="current" type="password" autocomplete="current-password" />
            </BFormGroup>

            <BFormGroup label="新密码">
                <BFormInput v-model="password" type="password" autocomplete="new-password" />
            </BFormGroup>

            <BFormGroup label="确认密码">
                <BFormInput v-model="confirm" type="password" autocomplete="new-password" />
            </BFormGroup>

            <BButton type="submit">保存新密码</BButton>
        </BCard>
    </BForm>
</template>
