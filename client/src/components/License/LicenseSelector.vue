<script setup lang="ts">
import { watchImmediate } from "@vueuse/core";
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";
import Multiselect from "vue-multiselect";

import { GalaxyApi } from "@/api";
import { type components } from "@/api/schema";
import { errorMessageAsString } from "@/utils/simple-error";

import License from "@/components/License/License.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const defaultLicense: LicenseType = {
    licenseId: null,
    name: "*Do not specify a license.*",
};

type LicenseMetadataModel = components["schemas"]["LicenseMetadataModel"];
type LicenseType = {
    licenseId: string | null;
    name: string;
};

interface Props {
    inputLicense: string | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onLicense", license: string | null): void;
}>();

const licensesLoading = ref(false);
const errorMessage = ref<string>("");
const currentLicense = ref<LicenseType>();
const licenses = ref<LicenseMetadataModel[] | undefined>([]);

const licenseOptions = computed(() => {
    const options: LicenseType[] = [];

    options.push(defaultLicense);

    for (const license of licenses.value || []) {
        if (license.licenseId == currentLicense.value?.licenseId || license.recommended) {
            options.push({
                licenseId: license.licenseId,
                name: license.name,
            });
        }
    }

    return options;
});

function onLicense(license: LicenseType) {
    emit("onLicense", license.licenseId);
}

async function fetchLicenses() {
    const { error, data } = await GalaxyApi().GET("/api/licenses");

    if (error) {
        errorMessage.value = errorMessageAsString(error) || "Unable to fetch licenses.";
    }

    licenses.value = data;

    licensesLoading.value = false;
}

async function setCurrentLicense() {
    if (!licenses.value?.length && !licensesLoading.value) {
        licensesLoading.value = true;

        await fetchLicenses();
    }

    const inputLicense = props.inputLicense;

    currentLicense.value = (licenses.value || []).find((l) => l.licenseId == inputLicense) || defaultLicense;
}

watchImmediate(
    () => props.inputLicense,
    () => {
        setCurrentLicense();
    }
);
</script>

<template>
    <div>
        <BAlert v-if="licensesLoading" variant="info" class="m-0" show>
            <LoadingSpan message="Loading licenses" />
        </BAlert>
        <BAlert v-else-if="errorMessage" variant="danger" class="m-0" show>
            {{ errorMessage }}
        </BAlert>
        <Multiselect
            v-else
            v-model="currentLicense"
            data-description="license select"
            track-by="licenseId"
            :options="licenseOptions"
            label="name"
            placeholder="Select a license"
            @select="onLicense" />
        <License v-if="currentLicense?.licenseId" :license-id="currentLicense.licenseId" />
    </div>
</template>
