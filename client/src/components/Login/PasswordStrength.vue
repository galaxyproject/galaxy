<script setup lang="ts">
import { ref, watch, type PropType } from "vue";
import zxcvbn from "zxcvbn"; // Import the zxcvbn library

// Props to receive the password input
const props = defineProps({
  password: {
    type: String as PropType<string | null>,
    required: true,
  },
});

const passwordStrength = ref<string>("empty");
const strengthScore = ref<number>(0);

const passwordRules = ref({
    minLength: false,
    hasNumber: false,
    hasUppercase: false,
    hasSpecialChar: false,
});

// Evaluate password strength using zxcvbn
function evaluatePasswordStrength(newPassword: string) {
  if (newPassword.length === 0) {
    passwordStrength.value = "empty";
    strengthScore.value = 0;
    return;
  }

  const result = zxcvbn(newPassword); // Analyze the password with zxcvbn
  strengthScore.value = result.score; // zxcvbn returns a score from 0 to 4

  // Map zxcvbn scores to strength labels
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

// Watch for changes in the password prop
watch(() => props.password, (newPassword) => {
  if (typeof newPassword === "string") {
    evaluatePasswordStrength(newPassword);
    validatePasswordRules(newPassword || "");
  }
});
</script>

<template>
    <div>
        <!-- Password Guidelines Button -->
        <BButton variant="info" class="mt-3" href="https://www.cisa.gov/secure-our-world/use-strong-passwords" target="_blank" rel="noopener noreferrer">
            Password Guidelines
        </BButton>

        <!-- Password Strength Bar -->
        <div class="password-strength-bar-container mt-2">
            <div
                class="password-strength-bar"
                :class="passwordStrength"
                :style="{ width: `${(strengthScore / 4) * 100}%` }"
            ></div>
        </div>

        <!-- Password Strength Text -->
        <div :class="['password-strength', passwordStrength]" class="mt-2">
            <span v-if="passwordStrength === 'empty'"></span>
            <span v-else-if="passwordStrength === 'weak'">Weak Password</span>
            <span v-else-if="passwordStrength === 'medium'">Medium Password</span>
            <span v-else>Strong Password</span>

        </div>

        <!-- Password Guidelines with check marker-->
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
