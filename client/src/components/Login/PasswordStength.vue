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
const showPasswordGuidelines = ref(false);

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

// Watch for changes in the password prop
watch(() => props.password, (newPassword) => {
  if (typeof newPassword === "string") {
    evaluatePasswordStrength(newPassword);
  }
});
</script>

<template>
    <div>
        <!-- Password Guidelines Button -->
        <BButton variant="info" class="mt-3" @click="showPasswordGuidelines = true">
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

        <!-- Password Guidelines -->
        <BModal v-model="showPasswordGuidelines" title="Tips for a secure Password">
            <p>A good password should meet the following criteria:</p>
            <ul>
                <li>At least 13 characters long.</li>
                <li>Use uppercase and lowercase letters.</li>
                <li>At least one number and one special character.</li>
                <li>Avoid common passwords like <code>123456</code> or <code>password</code>.</li>
                <li>No repeated patterns like <code>aaaa</code> or <code>123123</code>.</li>
            </ul>
            <template v-slot:modal-footer>
                <BButton variant="secondary" @click="showPasswordGuidelines = false">Close</BButton>
            </template>
        </BModal>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.password-strength-bar-container {
    background-color: #f0f0f0;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 5px;
}

.password-strength-bar {
    height: 100%;
    transition: width 0.3s ease;
}

.password-strength-bar.weak {
    background-color: $brand-danger;
}

.password-strength-bar.medium {
    background-color: $brand-warning;
}

.password-strength-bar.strong {
    background-color: $brand-success;
}

.password-strength.weak {
    color: $brand-danger;
}

.password-strength.medium {
    color: $brand-warning;
}

.password-strength.strong {
    color: $brand-success;
}
</style>
