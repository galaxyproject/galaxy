<script setup lang="ts">
import { watch, type PropType, type Ref, ref } from "vue";
import zxcvbn from "zxcvbn";

const props = defineProps({
    password: {
        type: String as PropType<string | null>,
        required: true,
    },
});

const passwordStrength = ref<string>("empty");
const strengthScore = ref<number>(0);
const showPasswordGuidelines: Ref<boolean> = ref(false);

const passwordRules = ref({
    minLength: false,
    hasNumber: false,
    hasUppercase: false,
    hasSpecialChar: false,
});

function evaluatePasswordStrength(newPassword: string) {
    if (newPassword.length === 0) {
        passwordStrength.value = "empty";
        strengthScore.value = 0;
        return;
    }

    const result = zxcvbn(newPassword);
    strengthScore.value = result.score;

    if (strengthScore.value === 0 || strengthScore.value === 1) {
        passwordStrength.value = "weak";
    } else if (strengthScore.value === 2 || strengthScore.value === 3) {
        passwordStrength.value = "medium";
    } else {
        passwordStrength.value = "strong";
    }
}

// Function to validate password rules
function validatePasswordRules(password: string) {
    passwordRules.value.minLength = password.length >= 12;
    passwordRules.value.hasNumber = /\d/.test(password);
    passwordRules.value.hasUppercase = /[A-Z]/.test(password);
    passwordRules.value.hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
}

watch(
    () => props.password,
    (newPassword) => {
        if (typeof newPassword === "string") {
            evaluatePasswordStrength(newPassword);
            validatePasswordRules(newPassword || "");
        }
    }
);
</script>

<template>
    <div>
        <BButton variant="info" class="mt-3" @click="showPasswordGuidelines = true"> Password Guidelines </BButton>

        <div>
            <BModal v-model="showPasswordGuidelines" title="Tips for a secure Password">
                <p>A good password should meet the following criteria:</p>
                <ul>
                    <li>At least 12 characters long.</li>
                    <li>Use uppercase and lowercase letters.</li>
                    <li>At least one number and one special character.</li>
                    <li>Avoid common passwords like <code>123456</code> or <code>password</code>.</li>
                    <li>No repeated patterns like <code>aaaa</code> or <code>123123</code>.</li>
                </ul>
                <p>
                    Learn more about:
                    <a
                        href="https://www.cisa.gov/secure-our-world/use-strong-passwords target="
                        target="_blank"
                        rel="noopener noreferrer"
                        >strong passwords</a
                    >.
                </p>
                <template v-slot:modal-footer>
                    <BButton variant="secondary" @click="showPasswordGuidelines = false">Schließen</BButton>
                </template>
            </BModal>
        </div>
        <div class="password-strength-bar-container mt-2">
            <div
                class="password-strength-bar"
                :class="passwordStrength"
                :style="{ width: `${(strengthScore / 4) * 100}%` }"></div>
        </div>

        <div :class="['password-strength', passwordStrength]" class="mt-2">
            <span v-if="passwordStrength === 'empty'"></span>
            <span v-else-if="passwordStrength === 'weak'">Weak Password</span>
            <span v-else-if="passwordStrength === 'medium'">Medium Password</span>
            <span v-else>Strong Password</span>
        </div>

        <div class="password-help">
            <ul>
                <li :class="{ 'rule-met': passwordRules.minLength }">
                    <i class="fa" :class="passwordRules.minLength ? 'fa-check' : 'fa-times'"></i>
                    At least 12 characters
                </li>
                <li :class="{ 'rule-met': passwordRules.hasNumber }">
                    <i class="fa" :class="passwordRules.hasNumber ? 'fa-check' : 'fa-times'"></i>
                    Contains a number
                </li>
                <li :class="{ 'rule-met': passwordRules.hasUppercase }">
                    <i class="fa" :class="passwordRules.hasUppercase ? 'fa-check' : 'fa-times'"></i>
                    Contains an uppercase letter
                </li>
                <li :class="{ 'rule-met': passwordRules.hasSpecialChar }">
                    <i class="fa" :class="passwordRules.hasSpecialChar ? 'fa-check' : 'fa-times'"></i>
                    Contains a special character
                </li>
            </ul>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.password-strength-bar-container {
    background-color: $gray-200;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 5px;
}

.password-strength-bar {
    height: 100%;
    transition: width 0.3s ease;

    &.weak {
        background-color: $brand-danger;
    }

    &.medium {
        background-color: $brand-warning;
    }

    &.strong {
        background-color: $brand-success;
    }
}

.password-strength {
    &.weak {
        color: $brand-danger;
    }

    &.medium {
        color: $brand-warning;
    }

    &.strong {
        color: $brand-success;
    }
}

.password-help ul {
    list-style: none;
    padding: 0;
}

.password-help li {
    display: flex;
    align-items: center;
    margin: 0.2rem;
}

.password-help li.rule-met {
    color: $brand-success;
}

.password-help li .fa {
    margin-right: 0.5rem;
}
</style>
