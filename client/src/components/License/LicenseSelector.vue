<script setup lang="ts">
import { faEdit, faSave, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormSelect } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { GalaxyApi } from "@/api";
import { type components } from "@/api/schema";
import { errorMessageAsString } from "@/utils/simple-error";

import License from "./License.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

type LicenseMetadataModel = components["schemas"]["LicenseMetadataModel"];

interface Props {
    inputLicense: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onLicense", license: string): void;
}>();

const editLicense = ref(false);
const licensesLoading = ref(true);
const errorMessage = ref<string>("");
const currentLicense = ref<string>(props.inputLicense);
const licenses = ref<LicenseMetadataModel[] | undefined>([]);

const currentLicenseInfo = computed(() => {
    for (const l of licenses.value || []) {
        if (l.licenseId == currentLicense.value) {
            return l;
        }
    }

    return null;
});
const licenseOptions = computed(() => {
    const options = [];

    options.push({
        value: null,
        text: "*Do not specify a license.*",
    });

    for (const l of licenses.value || []) {
        if (l.licenseId == currentLicense.value || l.recommended) {
            options.push({
                value: l.licenseId,
                text: l.name,
            });
        }
    }

    return options;
});

function onSave() {
    onLicense(currentLicense.value);
    disableEdit();
}

function disableEdit() {
    editLicense.value = false;
    errorMessage.value = "";
}

function onLicense(l: string) {
    emit("onLicense", l);
}

async function fetchLicenses() {
    const { error, data } = await GalaxyApi().GET("/api/licenses");

    if (error) {
        errorMessage.value = errorMessageAsString(error) || "Unable to fetch licenses.";
    }

    licenses.value = data;

    licensesLoading.value = false;
}

watch(
    () => props.inputLicense,
    (newLicense) => {
        currentLicense.value = newLicense;
    }
);

fetchLicenses();
</script>

<template>
    <div v-if="editLicense" class="license-selector">
        <LoadingSpan v-if="licensesLoading" message="Loading licenses" />
        <BAlert v-else-if="errorMessage" variant="danger" class="m-0" show>
            {{ errorMessage }}
        </BAlert>
        <BFormSelect v-else v-model="currentLicense" data-description="license select" :options="licenseOptions" />

        <License v-if="currentLicenseInfo" :license-id="currentLicense" :input-license-info="currentLicenseInfo">
            <template v-slot:buttons>
                <BButton v-b-tooltip.hover variant="outline-danger" title="Cancel Edit" @click="disableEdit">
                    <FontAwesomeIcon :icon="faTimes" data-description="license cancel" />
                    Cancel
                </BButton>
                <BButton v-b-tooltip.hover variant="primary" title="Save License" @click="onSave">
                    <FontAwesomeIcon :icon="faSave" data-description="license save" />
                    Save License
                </BButton>
            </template>
        </License>
        <div v-else>
            <BButton variant="outline-danger" @click="editLicense = false">
                <FontAwesomeIcon :icon="faTimes" data-description="license cancel" />
                Cancel
            </BButton>
            <BButton variant="primary" @click="onSave">
                <FontAwesomeIcon :icon="faSave" data-description="license save" />
                Save without license
            </BButton>
        </div>
    </div>
    <div
        v-else-if="currentLicense"
        data-description="license selector"
        :data-license="currentLicense"
        class="license-selector-edit">
        <License :license-id="currentLicense">
            <template v-slot:inline-buttons>
                <BButton
                    v-b-tooltip.hover
                    class="inline-icon-button"
                    variant="link"
                    size="sm"
                    title="Edit License"
                    @click="editLicense = true">
                    <FontAwesomeIcon :icon="faEdit" data-description="edit license link" fixed-width />
                </BButton>
            </template>
        </License>
    </div>
    <div v-else data-description="license selector" data-license="null">
        <i>
            <a href="#" data-description="edit license link" @click.prevent="editLicense = true">
                Specify a license for this workflow.
            </a>
        </i>
    </div>
</template>

<style scoped lang="scss">
.license-selector {
    display: grid;
    gap: 0.5em;
}
</style>
