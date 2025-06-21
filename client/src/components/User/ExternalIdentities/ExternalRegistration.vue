<script setup lang="ts">
import { BAlert, BForm } from "bootstrap-vue";
import { ref } from "vue";

import { capitalizeFirstLetter } from "@/utils/strings";

import type { OIDCConfigWithRegistration } from "./ExternalIDHelper";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    idpsWithRegistration: OIDCConfigWithRegistration;
    columnDisplay?: boolean;
}>();

const messageText = ref<string | null>(null);
const messageVariant = ref<string | null>(null);
</script>

<template>
    <div class="h-100">
        <BAlert v-if="messageText" show :variant="messageVariant">
            {{ messageText }}
        </BAlert>

        <BForm id="externalRegister" :class="{ 'd-flex h-100': !props.columnDisplay }">
            <div :class="!props.columnDisplay ? 'oidc-idps-column' : 'oidc-idps-grid'">
                <div v-for="(iDPInfo, idp) in props.idpsWithRegistration" :key="idp">
                    <GButton
                        v-if="iDPInfo['icon']"
                        transparent
                        class="d-block oidc-button p-0"
                        data-description="registration button"
                        :href="iDPInfo.end_user_registration_endpoint">
                        <img :src="iDPInfo['icon']" height="35" :alt="`Sign in with ${capitalizeFirstLetter(idp)}`" />
                    </GButton>
                    <GButton
                        v-else-if="iDPInfo['custom_button_text']"
                        class="d-block oidc-button"
                        color="blue"
                        outline
                        data-description="registration button"
                        :href="iDPInfo.end_user_registration_endpoint">
                        <i :class="props.idpsWithRegistration[idp]" />
                        Register with {{ iDPInfo["custom_button_text"] }}
                    </GButton>
                    <GButton
                        v-else
                        class="d-block oidc-button"
                        color="blue"
                        outline
                        data-description="registration button"
                        :href="iDPInfo.end_user_registration_endpoint">
                        <i :class="props.idpsWithRegistration[idp]" />
                        Register with
                        <span v-if="iDPInfo['label']">
                            {{ iDPInfo["label"].charAt(0).toUpperCase() + iDPInfo["label"].slice(1) }}
                        </span>
                        <span v-else>
                            {{ capitalizeFirstLetter(idp) }}
                        </span>
                    </GButton>
                </div>
            </div>
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
