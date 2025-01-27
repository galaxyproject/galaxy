<script setup lang="ts">
import { zxcvbn, zxcvbnOptions } from "@zxcvbn-ts/core";
import * as zxcvbnCommonPackage from "@zxcvbn-ts/language-common";
import * as zxcvbnEnPackage from "@zxcvbn-ts/language-en";
import { type PropType, type Ref, ref,watch } from "vue";

const props = defineProps({
    password: {
        type: String as PropType<string | null>,
        required: true,
    },
});

const passwordStrength = ref<string>("empty");
const strengthScore = ref<number>(0);
const showPasswordGuidelines: Ref<boolean> = ref(false);
const crackTime = ref<string>("");
const options = {
    translations: zxcvbnEnPackage.translations,
    graphs: zxcvbnCommonPackage.adjacencyGraphs,
    dictionary: {
        ...zxcvbnCommonPackage.dictionary,
        ...zxcvbnEnPackage.dictionary,
    },
};
zxcvbnOptions.setOptions(options);

function evaluatePasswordStrength(newPassword: string) {
    if (newPassword.length === 0) {
        passwordStrength.value = "empty";
        strengthScore.value = 0;
        crackTime.value = "";
        return;
    }

    const result = zxcvbn(newPassword);
    strengthScore.value = result.score;
    crackTime.value = String(result.crackTimesDisplay.offlineSlowHashing1e4PerSecond || "N/A");

    if (strengthScore.value <= 1) {
        passwordStrength.value = "weak";
    } else if (strengthScore.value <= 3) {
        passwordStrength.value = "medium";
    } else {
        passwordStrength.value = "strong";
    }
}

watch(
    () => props.password,
    (newPassword) => {
        if (typeof newPassword === "string") {
            evaluatePasswordStrength(newPassword);
        }
    }
);
</script>

<template>
    <div>
        <div class="password-strength-bar-container mt-2">
            <div
                class="password-strength-bar"
                :class="passwordStrength"
                :style="{ width: `${(strengthScore / 4) * 100}%` }"></div>
        </div>

        <div class="password-info-container mt-2">
            <div :class="['password-strength', passwordStrength]">
                <span v-if="passwordStrength === 'empty'"></span>
                <span v-else-if="passwordStrength === 'weak'">Weak Password</span>
                <span v-else-if="passwordStrength === 'medium'">Medium Password</span>
                <span v-else>Strong Password</span>
            </div>
            <div v-if="passwordStrength !== 'empty'" class="crack-time">
                <strong>Estimated time to crack:</strong>
                <span :class="passwordStrength"> {{ crackTime }}</span>
            </div>
        </div>

        <BButton variant="secondary" class="ui-link mt-3" @click="showPasswordGuidelines = true">
            Password Guidelines
        </BButton>

        <div>
            <BModal v-model="showPasswordGuidelines" title="Tips for a secure Password">
                <p>A good password should meet the following criteria:</p>
                <ul>
                    <li>At least 11 characters long.</li>
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

.password-info-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.password-strength,
.crack-time span {
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
