<script setup lang="ts">
import axios, { type AxiosError } from "axios";
import { BAlert, BButton, BForm, BFormCheckbox, BFormGroup } from "bootstrap-vue";
import { computed, onMounted, ref } from "vue";
import Multiselect from "vue-multiselect";
import {OIDCConfig, getOIDCIdpsWithRegistration, getNeedShowCilogonInstitutionList, submitOIDCLogon} from "components/User/ExternalIdentities/ExternalIDHelper"

import { useConfig } from "@/composables/config";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";
import { capitalizeFirstLetter } from "@/utils/strings";

import LoadingSpan from "@/components/LoadingSpan.vue";
import { useOpenUrl } from '@/composables/openurl';

interface Props {
    loginPage?: boolean;
    excludeIdps?: string[];
    disableLocalAccounts?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    loginPage: false,
    excludeIdps: () => [],
    disableLocalAccounts: false,
});

const { config, isConfigLoaded } = useConfig();

const loading = ref(false);
const messageText = ref<string | null>(null);
const messageVariant = ref<string | null>(null);

const oIDCIdps = computed<OIDCConfig>(() => (isConfigLoaded.value ? config.value.oidc : {}));

const filteredOIDCIdps = computed(() => {return getOIDCIdpsWithRegistration(oIDCIdps.value)});
const { openUrl } = useOpenUrl();


</script>

<template>
    <div>
        <BAlert :show="!!messageText" :variant="messageVariant">
            {{ messageText }}
        </BAlert>

        <BForm id="externalRRegister">
            <!-- OIDC registration-->
            <hr v-if="!disableLocalAccounts && Object.keys(filteredOIDCIdps).length > 0 " class="my-4" />
            <span v-if="isConfigLoaded">
                <div v-for="(iDPInfo, idp) in filteredOIDCIdps" :key="idp" class="m-1">
                    <span v-if="iDPInfo['icon']">
                        <BButton variant="link" class="d-block mt-3"
                            @click="openUrl(iDPInfo.end_user_registration_endpoint)">
                            <img :src="iDPInfo['icon']" height="45" :alt="idp" />
                        </BButton>
                    </span>
                    <span v-else-if="iDPInfo['custom_button_text']">
                        <BButton class="d-block mt-3" @click="openUrl(iDPInfo.end_user_registration_endpoint)">
                            <i :class="oIDCIdps[idp]" />
                            Register with {{ iDPInfo["custom_button_text"] }}
                        </BButton>
                    </span>
                    <span v-else>
                        <BButton class="d-block mt-3" @click="openUrl(iDPInfo.end_user_registration_endpoint)">
                            <i :class="oIDCIdps[idp]" />
                            Register with
                            <span v-if="iDPInfo['label']">
                                {{ iDPInfo["label"].charAt(0).toUpperCase() + iDPInfo["label"].slice(1) }}
                            </span>
                            <span v-else>
                                {{ capitalizeFirstLetter(idp) }}
                            </span>
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
