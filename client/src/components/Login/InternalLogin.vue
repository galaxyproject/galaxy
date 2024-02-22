<script setup lang="ts">
import { BButton, BForm, BFormGroup, BFormInput, BFormText } from "bootstrap-vue";
import { computed, type PropType, ref } from "vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

const router = useRouter();

// TODO: investigate why `PropType` is needed
interface Props {
    showAsBox?: boolean;
    passwordState: PropType<boolean> | null;
    connectExternalProvider: PropType<string> | null;
    connectExternalEmail: PropType<string> | null;
}

const props = withDefaults(defineProps<Props>(), {
    showAsBox: false,
    passwordState: null,
});

const emit = defineEmits<{
    (e: "submit-login", login: string | null, password: string | null): void;
    (e: "reset-login", login: string | null): void;
}>();

const labelNameAddress = localize("Public Name or Email Address");
const labelPassword = localize("Password");

const login = ref<string | null>(null);
const password = ref<string | null>(null);
const resetText = computed(() =>
    props.showAsBox ? localize("Forgot password?") : localize("Click here to reset your password.")
);

function resetClick() {
    if (!props.showAsBox) {
        emit("reset-login", login.value);
    } else {
        router.push("/login/start");
    }
}
</script>

<template>
    <BForm
        id="login"
        :inline="props.showAsBox"
        :class="{ 'd-flex align-items-baseline': props.showAsBox }"
        @submit.prevent="emit('submit-login', login, password)">
        <label v-if="!props.showAsBox" for="login-form-name">
            {{ labelNameAddress }}
        </label>
        <BFormInput
            v-if="props.showAsBox || !props.connectExternalProvider"
            id="login-form-name"
            v-model="login"
            name="login"
            :size="props.showAsBox ? 'sm' : undefined"
            :placeholder="props.showAsBox ? labelNameAddress : undefined"
            required
            type="text" />
        <BFormInput
            v-else
            id="login-form-name"
            disabled
            required
            :value="props.connectExternalEmail"
            name="login"
            type="text" />
        <!-- </BFormGroup> -->
        <BFormGroup :class="!props.showAsBox ? 'mt-2' : 'mr-2'">
            <label v-if="!props.showAsBox" for="login-form-password">
                {{ labelPassword }}
            </label>
            <BFormInput
                id="login-form-password"
                v-model="password"
                :state="props.passwordState"
                required
                :size="props.showAsBox ? 'sm' : undefined"
                :placeholder="props.showAsBox ? labelPassword : undefined"
                name="password"
                type="password" />
            <BFormText>
                <span v-if="!props.showAsBox" v-localize>Forgot password?</span>
                <a
                    v-b-tooltip.noninteractive.hover
                    :title="props.showAsBox ? 'Click here to reset your password' : undefined"
                    href="javascript:void(0)"
                    role="button"
                    @click.prevent="resetClick">
                    {{ resetText }}
                </a>
            </BFormText>
        </BFormGroup>
        <BButton v-localize name="login" type="submit" :size="props.showAsBox ? 'sm' : undefined">Login</BButton>
    </BForm>
</template>

<style scoped>
::-webkit-input-placeholder {
    font-style: italic;
}
:-moz-placeholder {
    font-style: italic;
}
::-moz-placeholder {
    font-style: italic;
}
:-ms-input-placeholder {
    font-style: italic;
}
</style>
