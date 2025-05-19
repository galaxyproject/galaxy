<script setup lang="ts">
import { BAlert, BButton, BForm } from "bootstrap-vue";
import { ref } from "vue";

import { useOpenUrl } from "@/composables/openurl";
import { capitalizeFirstLetter } from "@/utils/strings";

import type { OIDCConfigWithRegistration } from "./ExternalIDHelper";

const props = defineProps<{
    idpsWithRegistration: OIDCConfigWithRegistration;
}>();

const messageText = ref<string | null>(null);
const messageVariant = ref<string | null>(null);

const { openUrl } = useOpenUrl();
</script>

<template>
    <div>
        <BAlert :show="!!messageText" :variant="messageVariant">
            {{ messageText }}
        </BAlert>

        <BForm id="externalRRegister">
            <!-- OIDC registration-->
            <span>
                <div v-for="(iDPInfo, idp) in props.idpsWithRegistration" :key="idp" class="m-1">
                    <span v-if="iDPInfo['icon']">
                        <BButton
                            variant="link"
                            class="d-block mt-3"
                            data-description="registration button"
                            @click="openUrl(iDPInfo.end_user_registration_endpoint)">
                            <img :src="iDPInfo['icon']" height="45" :alt="idp" />
                        </BButton>
                    </span>
                    <span v-else-if="iDPInfo['custom_button_text']">
                        <BButton
                            class="d-block mt-3"
                            data-description="registration button"
                            @click="openUrl(iDPInfo.end_user_registration_endpoint)">
                            <i :class="props.idpsWithRegistration[idp]" />
                            Register with {{ iDPInfo["custom_button_text"] }}
                        </BButton>
                    </span>
                    <span v-else>
                        <BButton
                            class="d-block mt-3"
                            data-description="registration button"
                            @click="openUrl(iDPInfo.end_user_registration_endpoint)">
                            <i :class="props.idpsWithRegistration[idp]" />
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
