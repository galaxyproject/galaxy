<script setup lang="ts">
import {
    faBan,
    faCheck,
    faClock,
    faExclamationTriangle,
    faQuestionCircle,
    faTimes,
    faUser,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardBody, BCardFooter, BCardHeader } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, nextTick, ref, watch } from "vue";

import { isRegisteredUser } from "@/api";
import {
    decideDeviceAuthorization,
    type DeviceAuthorizationDetails,
    DeviceAuthorizationError,
    type DeviceAuthorizationErrorReason,
    fetchDeviceAuthorization,
} from "@/api/oauth";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GForm from "@/components/BaseComponents/Form/GForm.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GFormLabel from "@/components/BaseComponents/Form/GFormLabel.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import SuccessIconOverlay from "@/components/Common/SuccessIndicator/SuccessIconOverlay.vue";
import UtcDate from "@/components/UtcDate.vue";

interface PageError {
    message: string;
    /** Set when the code itself is the problem, so retrying it can't work. */
    reason?: DeviceAuthorizationErrorReason;
}

const REASON_ICONS = { unknown: faQuestionCircle, expired: faClock, used: faBan };

/** The `XXXX-XXXX` style user code entered by the user. */
const userCode = ref("");

/** The fetched device authorization details for the entered code. */
const details = ref<DeviceAuthorizationDetails | null>(null);
const decision = ref<"approved" | "denied" | null>(null);
const loading = ref(false);
const codeError = ref<PageError | null>(null);
const decisionError = ref<PageError | null>(null);

/** The last code that failed for good, so Continue stays off until the user changes it. */
const failedCode = ref("");

const { currentUser } = storeToRefs(useUserStore());
const username = computed(() => (isRegisteredUser(currentUser.value) && currentUser.value.username) || "");

const canLookUp = computed(() => !loading.value && userCode.value !== failedCode.value);
const codeState = computed(() => (codeError.value ? false : null));

const codeInput = ref<InstanceType<typeof GFormInput>>();

// Ensure the user cannot type invalid characters or exceed the expected format for the user code.
watch(userCode, async (value) => {
    const formatted = formatUserCode(value);
    if (formatted !== value) {
        // Runs this watcher again with the formatted code
        userCode.value = formatted;
        // A dropped keystroke (e.g. a 10th letter) restores the previous value, which Vue doesn't re-render
        await nextTick();
        const element = codeInput.value?.getInputElement();
        if (element && element.value !== formatted) {
            element.value = formatted;
        }
        return;
    }
    codeError.value = null;
});

/**
 * Format typed or pasted text as a user code like `WDJB-MJHT`: uppercase letters only
 * (codes have no digits), with the dash added before the 5th letter.
 */
function formatUserCode(value: string): string {
    const letters = value
        .toUpperCase()
        .replace(/[^A-Z]/g, "")
        .slice(0, 8);
    if (letters.length > 4) {
        return `${letters.slice(0, 4)}-${letters.slice(4)}`;
    }
    // Keep a dash the user typed after the 4th letter
    return letters.length === 4 && value.endsWith("-") ? `${letters}-` : letters;
}

/** Convert an unknown error into a `PageError` made for this component as it includes a `reason`. */
function toPageError(e: unknown, defaultMessage: string): PageError {
    return {
        message: errorMessageAsString(e, defaultMessage),
        reason: e instanceof DeviceAuthorizationError ? e.reason : undefined,
    };
}

function errorIcon(error: PageError) {
    return error.reason ? REASON_ICONS[error.reason] : faExclamationTriangle;
}

/**
 * Given the user has entered a code, look up the corresponding device authorization details.
 *
 * This includes creation and expiry times, requested scopes, client information, and other
 * relevant details.
 */
async function lookUpCode() {
    loading.value = true;
    try {
        details.value = await fetchDeviceAuthorization(userCode.value.trim());
    } catch (e) {
        codeError.value = toPageError(e, "Could not look up this code.");
        failedCode.value = codeError.value.reason ? userCode.value : "";
    } finally {
        loading.value = false;
    }
}

/**
 * Decide whether to approve or deny the device authorization for the entered code.
 * @param approve Whether to approve (`true`) or deny (`false`) the device authorization.
 */
async function decide(approve: boolean) {
    if (!details.value) {
        return;
    }
    loading.value = true;
    decisionError.value = null;
    try {
        await decideDeviceAuthorization(details.value.user_code, approve);
        decision.value = approve ? "approved" : "denied";
    } catch (e) {
        decisionError.value = toPageError(e, "Could not save your answer.");
    } finally {
        loading.value = false;
    }
}

/** Reset the device verification form to its initial state. */
function reset() {
    userCode.value = "";
    details.value = null;
    decision.value = null;
    decisionError.value = null;
    failedCode.value = "";
}
</script>

<template>
    <div class="device-verification">
        <div class="d-flex justify-content-md-center">
            <div>
                <GAlert :show="!!decisionError" variant="danger">
                    <template v-if="decisionError">
                        <FontAwesomeIcon :icon="errorIcon(decisionError)" fixed-width />
                        {{ decisionError.message }}
                    </template>
                </GAlert>

                <p v-if="username" id="device-signed-in-as" class="text-muted small text-center mb-2">
                    <FontAwesomeIcon :icon="faUser" fixed-width />
                    {{ localize("Signed in as") }} <b>{{ username }}</b>
                </p>

                <BCard no-body class="device-verification-card">
                    <!-- 1. Enter the code from the requesting application/device -->
                    <template v-if="!details">
                        <BCardHeader>{{ localize("Log in an app to your Galaxy account") }}</BCardHeader>
                        <BCardBody>
                            <GForm id="device-code-form" @submit.prevent="lookUpCode">
                                <GFormLabel :title="localize('Enter the code shown in your application')">
                                    <GFormInput
                                        id="device-user-code"
                                        ref="codeInput"
                                        v-model="userCode"
                                        required
                                        autocomplete="off"
                                        spellcheck="false"
                                        placeholder="XXXX-XXXX"
                                        :state="codeState"
                                        :aria-describedby="codeError ? 'device-user-code-feedback' : undefined"
                                        class="device-user-code" />
                                </GFormLabel>
                                <!-- Not GFormLabel's `invalid-feedback`, which takes plain text, so the `reason` icon fits -->
                                <span v-if="codeError" id="device-user-code-feedback" class="device-user-code-feedback">
                                    <FontAwesomeIcon :icon="errorIcon(codeError)" fixed-width />
                                    {{ codeError.message }}
                                </span>
                                <GButton
                                    type="submit"
                                    color="blue"
                                    :disabled="!canLookUp"
                                    inline
                                    class="w-100 mt-2 py-1">
                                    {{ localize("Continue") }}
                                </GButton>
                            </GForm>
                        </BCardBody>
                        <BCardFooter>
                            {{ localize("Only enter a code from a login you started yourself.") }}
                        </BCardFooter>
                    </template>

                    <!-- 2. Review the request and approve or deny it -->
                    <template v-else-if="!decision">
                        <BCardHeader>
                            <b>{{ details.app_name }}</b> {{ localize("wants to access your Galaxy account") }}
                        </BCardHeader>
                        <BCardBody>
                            <p class="mb-1">{{ localize("It asks to:") }}</p>
                            <ul v-if="details.scopes.length" class="device-scopes">
                                <li v-for="scope in details.scopes" :key="scope">
                                    <code>{{ scope }}</code>
                                </li>
                            </ul>
                            <ul v-else class="device-scopes">
                                <li>{{ localize("Access your Galaxy account") }}</li>
                            </ul>
                            <p class="text-muted small mb-3">
                                {{ localize("Requested") }}
                                <span v-if="details.requesting_ip">
                                    {{ localize("from") }} <code>{{ details.requesting_ip }}</code>
                                </span>
                                <UtcDate :date="details.create_time" mode="elapsed" />.
                                {{ localize("This code expires") }}
                                <UtcDate :date="details.expires_at" mode="elapsed" />.
                            </p>
                            <!-- The code is unknown, expired or used, so approving or denying can't work anymore -->
                            <GButton
                                v-if="decisionError?.reason"
                                id="device-start-over"
                                color="blue"
                                inline
                                class="w-100 py-1"
                                @click="reset">
                                {{ localize("Enter a different code") }}
                            </GButton>
                            <div v-else class="d-flex justify-content-between flex-gapx-1">
                                <GButton
                                    id="device-deny"
                                    class="w-100"
                                    outline
                                    :disabled="loading"
                                    @click="decide(false)">
                                    {{ localize("Deny") }}
                                </GButton>
                                <GButton
                                    id="device-approve"
                                    class="w-100"
                                    color="blue"
                                    :disabled="loading"
                                    @click="decide(true)">
                                    {{ localize("Approve") }}
                                </GButton>
                            </div>
                        </BCardBody>
                        <BCardFooter v-if="!decisionError?.reason">
                            {{ localize("Only approve if you started this login and recognize the app.") }}
                            <GLink @click="reset">{{ localize("Enter a different code.") }}</GLink>
                        </BCardFooter>
                    </template>

                    <!-- 3. Done -->
                    <template v-else>
                        <BCardHeader v-if="decision === 'approved'" class="d-flex align-items-center">
                            <SuccessIconOverlay :covered-icon="faCheck" class="text-success mr-1" />
                            {{ localize("Login approved") }}
                        </BCardHeader>
                        <BCardHeader v-else class="d-flex align-items-center">
                            <FontAwesomeIcon :icon="faTimes" fixed-width class="text-danger mr-1" />
                            {{ localize("Login denied") }}
                        </BCardHeader>
                        <BCardBody>
                            <p v-if="decision === 'approved'" class="mb-0">
                                <b>{{ details.app_name }}</b>
                                {{
                                    localize("is now logged in. You can close this tab and return to your application.")
                                }}
                            </p>
                            <p v-else class="mb-0">
                                <b>{{ details.app_name }}</b> {{ localize("did not get access to your account.") }}
                            </p>
                        </BCardBody>
                    </template>
                </BCard>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.device-verification {
    margin: 1rem 10rem;
}
.device-verification-card {
    width: 26rem;
    max-width: 100%;
}
.device-user-code {
    font-family: monospace;
    font-size: 1.25rem;
    letter-spacing: 0.15em;
    text-align: center;
}
// Same colour as GFormLabel's invalid feedback
.device-user-code-feedback {
    display: block;
    color: var(--color-red-600);
}
.device-scopes {
    padding-left: 1.25rem;
}
</style>
