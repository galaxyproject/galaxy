<script setup lang="ts">
import axios, { type AxiosError } from "axios";
import { BAlert, BButton, BButtonGroup, BForm, BFormCheckbox, BFormGroup } from "bootstrap-vue";
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
const cilogonOrCustos = ref<"cilogon" | "custos" | null>(null);
const toggleCilogon = ref(false);

const oIDCIdps = computed<OIDCConfig>(() => (isConfigLoaded.value ? config.value.oidc : {}));

const filteredOIDCIdps = computed(() => {
    return getFilteredOIDCIdps(oIDCIdps.value, props.excludeIdps);
});

const cilogonListShow = computed(() => {
    return getNeedShowCilogonInstitutionList(oIDCIdps.value);
});

const cILogonEnabled = computed(() => oIDCIdps.value.cilogon);
const custosEnabled = computed(() => oIDCIdps.value.custos);

onMounted(async () => {
    rememberIdp.value = getIdpPreference() !== null;

    // Only fetch CILogonIDPs if custos/cilogon configured
    if (cilogonListShow.value) {
        await getCILogonIdps();
    }
});

function toggleCILogon(idp: "cilogon" | "custos") {
    if (cilogonOrCustos.value === idp || cilogonOrCustos.value === null) {
        toggleCilogon.value = !toggleCilogon.value;
    }
    cilogonOrCustos.value = toggleCilogon.value ? idp : null;
}

async function clickOIDCLogin(idp: string) {
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
        const redirect_uri = await submitCILogon(idp, true, selected.value.EntityID);

        localStorage.setItem("galaxy-provider", idp);

        if (redirect_uri) {
            window.location.href = redirect_uri;
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

        <BForm id="externalLogin" :class="{ 'd-flex h-100': !props.columnDisplay }">
            <!-- OIDC login-->
            <div v-if="cilogonListShow" class="cilogon">
                <div v-if="props.loginPage">
                    <!--Only Display if CILogon/Custos is configured-->
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

                    <BButton
                        v-if="cILogonEnabled"
                        :disabled="loading || selected === null"
                        @click="clickCILogin('cilogon')">
                        <LoadingSpan v-if="loading" message="Signing In" />
                        <span v-else>Sign in with Institutional Credentials*</span>
                    </BButton>
                    <!--convert to v-else-if to allow only one or the other. if both enabled, put the one that should be default first-->
                    <BButton
                        v-if="Object.prototype.hasOwnProperty.call(oIDCIdps, 'custos')"
                        :disabled="loading || selected === null"
                        @click="clickCILogin('custos')">
                        <LoadingSpan v-if="loading" message="Signing In" />
                        <span v-else>Sign in with Custos*</span>
                    </BButton>
                </div>

                <div v-else>
                    <BButtonGroup class="w-100">
                        <BButton
                            v-if="cILogonEnabled"
                            :pressed="cilogonOrCustos === 'cilogon'"
                            @click="toggleCILogon('cilogon')">
                            Sign in with Institutional Credentials*
                        </BButton>

                        <BButton
                            v-if="custosEnabled"
                            :pressed="cilogonOrCustos === 'custos'"
                            @click="toggleCILogon('custos')">
                            Sign in with Custos*
                        </BButton>
                    </BButtonGroup>

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

                        <BButton
                            v-if="toggleCilogon"
                            class="mt-1"
                            :disabled="loading || selected === null"
                            @click="clickCILogin(cilogonOrCustos)">
                            Login via {{ cilogonOrCustos === "cilogon" ? "CILogon" : "Custos" }} *
                        </BButton>
                    </BFormGroup>
                </div>

                <p class="mt-3">
                    <small class="text-muted">
                        * Galaxy uses CILogon via Custos to enable you to log in from this organization. By clicking
                        'Sign In', you agree to the
                        <a href="https://ca.cilogon.org/policy/privacy">CILogon</a> privacy policy and you agree to
                        share your username, email address, and affiliation with CILogon, Custos, and Galaxy.
                    </small>
                </p>
            </div>

            <template v-if="cilogonListShow && Object.keys(filteredOIDCIdps).length > 0">
                <VerticalSeparator v-if="!props.columnDisplay">
                    <span v-localize>or</span>
                </VerticalSeparator>

                <hr v-else class="w-100" />
            </template>

            <span
                v-if="isConfigLoaded"
                :class="!props.columnDisplay && props.loginPage ? 'oidc-idps-column' : 'oidc-idps-grid'">
                <div v-for="(iDPInfo, idp) in filteredOIDCIdps" :key="idp">
                    <BButton
                        v-if="iDPInfo['icon']"
                        variant="link"
                        class="d-block oidc-button p-0 text-decoration-none"
                        :disabled="loading"
                        @click="clickOIDCLogin(idp)">
                        <img :src="iDPInfo['icon']" height="35" :alt="`Sign in with ${capitalizeFirstLetter(idp)}`" />
                    </BButton>
                    <BButton
                        v-else-if="iDPInfo['custom_button_text']"
                        variant="outline-primary"
                        class="d-block oidc-button"
                        :disabled="loading"
                        @click="clickOIDCLogin(idp)">
                        <i :class="oIDCIdps[idp]" />
                        Sign in with {{ iDPInfo["custom_button_text"] }}
                    </BButton>
                    <BButton
                        v-else
                        variant="outline-primary"
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
                    </BButton>
                </div>
            </span>
        </BForm>
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
