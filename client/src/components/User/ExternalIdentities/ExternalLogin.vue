<script setup lang="ts">
import axios, { type AxiosError } from "axios";
import { BAlert, BButton, BForm, BFormCheckbox, BFormGroup } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";
import Multiselect from "vue-multiselect";

import { useConfig } from "@/composables/config";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Idp {
    DisplayName: string;
    EntityID: string;
    OrganizationName: string;
    RandS: boolean;
}
type OIDCConfig = Record<string, { icon?: string }>;

interface Props {
    loginPage?: boolean;
    excludeIdps?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    loginPage: false,
    excludeIdps: () => [],
});

const { config, isConfigLoaded } = useConfig();

const loading = ref(false);
const messageText = ref<string | null>(null);
const messageVariant = ref<string | null>(null);
const cILogonIdps = ref<Idp[]>([]);
const selected = ref<Idp | null>(null);
const rememberIdp = ref(false);
const cilogonOrCustos = ref<string | null>(null);
const toggleCilogon = ref(false);

const oIDCIdps = computed<OIDCConfig>(() => (isConfigLoaded.value ? config.value.oidc : {}));

const filteredOIDCIdps = computed(() => {
    const exclude = ["cilogon", "custos"].concat(props.excludeIdps);
    const filtered = Object.assign({}, oIDCIdps.value);

    exclude.forEach((idp) => {
        delete filtered[idp];
    });

    return filtered;
});

const cilogonListShow = computed(() => {
    return oIDCIdps.value.cilogon || oIDCIdps.value.custos;
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

function toggleCILogon(idp: string) {
    toggleCilogon.value = !toggleCilogon.value;
    cilogonOrCustos.value = toggleCilogon.value ? idp : null;
}

async function submitOIDCLogin(idp: string) {
    loading.value = true;

    try {
        const loginUrl = withPrefix(`/authnz/${idp}/login`);
        const urlParams = new URLSearchParams(window.location.search);
        const redirectParam = urlParams.get("redirect");

        const formData = new FormData();
        formData.append("next", redirectParam || "");

        const { data } = await axios.post(loginUrl, formData, { withCredentials: true });

        if (data.redirect_uri) {
            window.location = data.redirect_uri;
        }
    } catch (e) {
        messageVariant.value = "danger";
        messageText.value = errorMessageAsString(e, "Login failed for an unknown reason.");
    } finally {
        loading.value = false;
    }
}

async function submitCILogon(idp: string | null) {
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
        const { data } = await axios.post(withPrefix(`/authnz/${idp}/login/?idphint=${selected.value.EntityID}`));

        localStorage.setItem("galaxy-provider", idp);

        if (data.redirect_uri) {
            window.location = data.redirect_uri;
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
    <div>
        <BAlert :show="messageText" :variant="messageVariant">
            {{ messageText }}
        </BAlert>

        <BForm id="externalLogin">
            <!-- OIDC login-->
            <hr class="my-4" />

            <div v-if="cilogonListShow" class="cilogon">
                <div v-if="props.loginPage">
                    <!--Only Display if CILogon/Custos is configured-->
                    <BFormGroup label="Use existing institutional login">
                        <Multiselect
                            v-model="selected"
                            placeholder="Select your institution"
                            :options="cILogonIdps"
                            label="DisplayName"
                            :deselect-label="null"
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
                        @click="submitCILogon('cilogon')">
                        <LoadingSpan v-if="loading" message="Signing In" />
                        <span v-else>Sign in with Institutional Credentials*</span>
                    </BButton>
                    <!--convert to v-else-if to allow only one or the other. if both enabled, put the one that should be default first-->
                    <BButton
                        v-if="Object.prototype.hasOwnProperty.call(oIDCIdps, 'custos')"
                        :disabled="loading || selected === null"
                        @click="submitCILogon('custos')">
                        <LoadingSpan v-if="loading" message="Signing In" />
                        <span v-else>Sign in with Custos*</span>
                    </BButton>
                </div>

                <div v-else>
                    <BButton v-if="cILogonEnabled" @click="toggleCILogon('cilogon')">
                        Sign in with Institutional Credentials*
                    </BButton>

                    <BButton v-if="custosEnabled" @click="toggleCILogon('custos')">Sign in with Custos*</BButton>

                    <BFormGroup v-if="toggleCilogon">
                        <Multiselect
                            v-model="selected"
                            placeholder="Select your institution"
                            :options="cILogonIdps"
                            label="DisplayName"
                            :deselect-label="null"
                            :allow-empty="false"
                            track-by="EntityID" />

                        <BButton
                            v-if="toggleCilogon"
                            :disabled="loading || selected === null"
                            @click="submitCILogon(cilogonOrCustos)">
                            Login*
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

            <span v-if="isConfigLoaded">
                <div v-for="(iDPInfo, idp) in filteredOIDCIdps" :key="idp" class="m-1">
                    <span v-if="iDPInfo['icon']">
                        <BButton variant="link" class="d-block mt-3" @click="submitOIDCLogin(idp)">
                            <img :src="iDPInfo['icon']" height="45" :alt="idp" />
                        </BButton>
                    </span>
                    <span v-else-if="iDPInfo['custom_button_text']">
                        <BButton class="d-block mt-3" @click="submitOIDCLogin(idp)">
                            <i :class="oIDCIdps[idp]" />
                            Sign in with {{ iDPInfo["custom_button_text"] }}
                        </BButton>
                    </span>
                    <span v-else>
                        <BButton class="d-block mt-3" @click="submitOIDCLogin(idp)">
                            <i :class="oIDCIdps[idp]" />
                            Sign in with
                            {{ idp.charAt(0).toUpperCase() + idp.slice(1) }}
                        </BButton>
                    </span>
                </div>
            </span>
        </BForm>
    </div>
</template>

<style scoped>
.card-body {
    overflow: visible;
}
</style>
