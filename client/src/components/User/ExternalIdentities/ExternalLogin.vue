<script setup lang="ts">
import axios, { type AxiosError } from "axios";
import { BAlert, BForm, BFormCheckbox, BFormGroup } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";
import Multiselect from "vue-multiselect";

import {
    getFilteredOIDCIdps,
    getNeedShowCilogonInstitutionList,
    type OIDCConfig,
    submitCILogon,
    submitOIDCLogon,
} from "@/components/User/ExternalIdentities/ExternalIDHelper";
import { useConfig } from "@/composables/config";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";
import { capitalizeFirstLetter } from "@/utils/strings";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import VerticalSeparator from "@/components/Common/VerticalSeparator.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Idp {
    DisplayName: string;
    EntityID: string;
    OrganizationName: string;
    RandS: boolean;
}

interface Props {
    loginPage?: boolean;
    excludeIdps?: string[];
    columnDisplay?: boolean;
    disableLocalAccounts?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    loginPage: false,
    excludeIdps: () => [],
    columnDisplay: true,
    disableLocalAccounts: false,
});

const { config, isConfigLoaded } = useConfig();

const loading = ref(false);
const messageText = ref<string | null>(null);
const messageVariant = ref<string | null>(null);
const cILogonIdps = ref<Idp[]>([]);
const selected = ref<Idp | null>(null);
const rememberIdp = ref(false);
const cilogon = ref<"cilogon" | null>(null);
const toggleCilogon = ref(false);

const oIDCIdps = computed<OIDCConfig>(() => (isConfigLoaded.value ? config.value.oidc : {}));

const filteredOIDCIdps = computed(() => getFilteredOIDCIdps(oIDCIdps.value, props.excludeIdps));

const cilogonListShow = computed(() => getNeedShowCilogonInstitutionList(oIDCIdps.value));

const cILogonEnabled = computed(() => oIDCIdps.value.cilogon);

onMounted(async () => {
    rememberIdp.value = getIdpPreference() !== null;

    // Only fetch CILogonIDPs if cilogon configured
    if (cilogonListShow.value) {
        await getCILogonIdps();
    }
});

function toggleCILogon(idp: "cilogon") {
    if (cilogon.value === idp || cilogon.value === null) {
        toggleCilogon.value = !toggleCilogon.value;
    }
    cilogon.value = toggleCilogon.value ? idp : null;
}

async function clickOIDCLogin(idp: string) {
    if (loading.value) {
        return;
    }
    loading.value = true;

    try {
        const urlParams = new URLSearchParams(window.location.search);
        const redirectParam = urlParams.get("redirect");
        const redirectUri = await submitOIDCLogon(idp, redirectParam);
        if (redirectUri) {
            window.location.href = redirectUri;
        }
    } catch (e) {
        messageVariant.value = "danger";
        messageText.value = errorMessageAsString(e, "Login failed for an unknown reason.");
    } finally {
        loading.value = false;
    }
}

async function clickCILogin(idp: string | null) {
    if (loading.value) {
        return;
    }
    if (props.loginPage) {
        setIdpPreference();
    }

    if (!selected.value || !idp) {
        messageVariant.value = "danger";
        messageText.value = "Please select an institution.";
        return;
    }

    loading.value = true;

    try {
        const redirectUri = await submitCILogon(idp, true, selected.value.EntityID);

        localStorage.setItem("galaxy-provider", idp);

        if (redirectUri) {
            window.location.href = redirectUri;
        }
    } catch (e) {
        messageVariant.value = "danger";
        messageText.value = errorMessageAsString(e, "Login failed for an unknown reason.");
    } finally {
        loading.value = false;
    }
}

async function getCILogonIdps() {
    try {
        const { data } = await axios.get(withPrefix("/authnz/get_cilogon_idps"));

        cILogonIdps.value = data;

        if (cILogonIdps.value.length == 1) {
            selected.value = cILogonIdps.value[0]!;
        } else {
            // List is originally sorted by OrganizationName which can be different from DisplayName
            cILogonIdps.value.sort((a, b) => (a.DisplayName > b.DisplayName ? 1 : -1));
        }

        if (props.loginPage) {
            const preferredIdp = getIdpPreference();

            if (preferredIdp) {
                const selectedIdp = cILogonIdps.value.find((idp) => idp.EntityID === preferredIdp);

                if (selectedIdp) {
                    selected.value = selectedIdp;
                }
            }
        }
    } catch (e) {
        const error = e as AxiosError<{ err_msg?: string }>;
        messageVariant.value = "danger";
        const message = error.response?.data && error.response.data.err_msg;
        messageText.value = message || "Failed to fetch CILogon IdPs.";
    }
}

function setIdpPreference() {
    if (rememberIdp.value && selected.value) {
        localStorage.setItem("galaxy-remembered-idp", selected.value.EntityID);
    } else {
        localStorage.removeItem("galaxy-remembered-idp");
    }
}

function getIdpPreference() {
    return localStorage.getItem("galaxy-remembered-idp");
}
</script>

<template>
    <div class="h-100">
        <BAlert v-if="messageText" class="text-nowrap" show :variant="messageVariant">
            {{ messageText }}
        </BAlert>

        <div :class="{ 'd-flex h-100': !props.columnDisplay }">
            <!-- OIDC login-->
            <BForm v-if="cilogonListShow" id="externalLogin" class="cilogon">
                <div v-if="props.loginPage">
                    <!--Only Display if CILogon is configured-->
                    <BFormGroup label="Use existing institutional login">
                        <Multiselect
                            v-model="selected"
                            placeholder="Select your institution"
                            :options="cILogonIdps"
                            label="DisplayName"
                            select-label=""
                            deselect-label=""
                            :allow-empty="false"
                            track-by="EntityID" />
                    </BFormGroup>

                    <BFormGroup v-if="props.loginPage">
                        <BFormCheckbox id="remember-idp" v-model="rememberIdp">
                            Remember institution selection
                        </BFormCheckbox>
                    </BFormGroup>

                    <GButton
                        v-if="cILogonEnabled"
                        :disabled="loading || selected === null"
                        @click="clickCILogin('cilogon')">
                        <LoadingSpan v-if="loading" message="Signing In" />
                        <span v-else>Sign in with Institutional Credentials*</span>
                    </GButton>

                </div>

                <div v-else>
                    <GButtonGroup class="w-100">
                        <GButton
                            v-if="cILogonEnabled"
                            :pressed="cilogon === 'cilogon'"
                            @click="toggleCILogon('cilogon')">
                            Sign in with Institutional Credentials*
                        </GButton>

                    </GButtonGroup>

                    <BFormGroup v-if="toggleCilogon" class="mt-1">
                        <Multiselect
                            v-model="selected"
                            placeholder="Select your institution"
                            :options="cILogonIdps"
                            label="DisplayName"
                            select-label=""
                            deselect-label=""
                            :allow-empty="false"
                            track-by="EntityID" />

                        <GButton
                            v-if="toggleCilogon"
                            class="mt-1"
                            :disabled="loading || selected === null"
                            @click="clickCILogin(cilogon)">
                            Login via CILogon *
                        </GButton>
                    </BFormGroup>
                </div>

                <p class="mt-3">
                    <small class="text-muted">
                        * Galaxy uses CILogon to enable you to log in from this organization. By clicking
                        'Sign In', you agree to the
                        <a href="https://ca.cilogon.org/policy/privacy">CILogon</a> privacy policy and you agree to
                        share your username, email address, and affiliation with CILogon and Galaxy.
                    </small>
                </p>
            </BForm>

            <template v-if="cilogonListShow && Object.keys(filteredOIDCIdps).length > 0">
                <VerticalSeparator v-if="!props.columnDisplay">
                    <span v-localize>or</span>
                </VerticalSeparator>

                <hr v-else class="w-100" />
            </template>

            <div
                v-if="isConfigLoaded"
                :class="!props.columnDisplay && props.loginPage ? 'oidc-idps-column' : 'oidc-idps-grid'">
                <div v-for="(iDPInfo, idp) in filteredOIDCIdps" :key="idp">
                    <GButton
                        v-if="iDPInfo['icon']"
                        transparent
                        class="d-block oidc-button p-0"
                        :disabled="loading"
                        @click="clickOIDCLogin(idp)">
                        <img :src="iDPInfo['icon']" height="35" :alt="`Sign in with ${capitalizeFirstLetter(idp)}`" />
                    </GButton>
                    <GButton
                        v-else-if="iDPInfo['custom_button_text']"
                        color="blue"
                        outline
                        class="d-block oidc-button"
                        :disabled="loading"
                        @click="clickOIDCLogin(idp)">
                        <i :class="oIDCIdps[idp]" />
                        Sign in with {{ iDPInfo["custom_button_text"] }}
                    </GButton>
                    <GButton
                        v-else
                        color="blue"
                        outline
                        class="d-block oidc-button"
                        :disabled="loading"
                        @click="clickOIDCLogin(idp)">
                        <i :class="oIDCIdps[idp]" />
                        Sign in with
                        <span v-if="iDPInfo['label']">
                            {{ iDPInfo["label"].charAt(0).toUpperCase() + iDPInfo["label"].slice(1) }}
                        </span>
                        <span v-else>
                            {{ capitalizeFirstLetter(idp) }}
                        </span>
                    </GButton>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.card-body {
    overflow: visible;
}
/* Enforce idps to appear in a column */
.oidc-idps-column {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    height: 100%;
    justify-content: center;
    .oidc-button {
        width: 100%;
        display: flex !important;
        justify-content: center;
    }
}
/* Flexible grid for idps */
.oidc-idps-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.5rem;
    width: 100%;
    height: 100%;
    justify-items: center;
}
</style>
