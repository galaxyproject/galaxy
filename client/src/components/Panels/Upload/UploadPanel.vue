<script setup lang="ts">
import { faCompass, faSlidersH } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref } from "vue";

import { useConfig } from "@/composables/config";

import type { UploadMethodConfig, UploadMode } from "./types";
import { getAllUploadMethods } from "./uploadMethodRegistry";

import UploadMethodDialog from "./UploadMethodDialog.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

const { config, isConfigLoaded } = useConfig();

const query = ref("");
const showModal = ref(false);
const showGuidedModal = ref(false);
const showAdvancedModal = ref(false);
const selectedMethod = ref<UploadMode | null>(null);

const allUploadMethods = getAllUploadMethods();

const availableMethods = computed(() => {
    if (!isConfigLoaded.value) {
        return allUploadMethods;
    }

    return allUploadMethods.filter((method) => {
        // Filter based on config requirements
        if (method.requiresConfig) {
            return method.requiresConfig.every((configKey) => config.value[configKey]);
        }
        return true;
    });
});

const filteredMethods = computed(() => {
    const rawTokens = query.value.trim().split(/\s+/).filter(Boolean);
    if (rawTokens.length === 0) {
        return availableMethods.value;
    }
    const tokens = rawTokens.map((token) => token.toLowerCase());
    return availableMethods.value.filter((method) => {
        const searchText = `${method.name} ${method.description}`.toLowerCase();
        return tokens.every((token) => searchText.includes(token));
    });
});

function selectUploadMethod(method: UploadMethodConfig) {
    selectedMethod.value = method.id;
    showModal.value = true;
}

function closeModal() {
    showModal.value = false;
    selectedMethod.value = null;
}

function openAdvancedMode() {
    showAdvancedModal.value = true;
}

function openGuidedMode() {
    showGuidedModal.value = true;
}
</script>

<template>
    <div class="upload-panel-wrapper">
        <ActivityPanel title="Import Data" data-description="beta upload panel">
            <template v-slot:header-buttons>
                <BButton
                    v-b-tooltip.hover.bottom.noninteractive
                    title="Import data using a guided wizard"
                    variant="link"
                    size="sm"
                    @click="openGuidedMode">
                    <FontAwesomeIcon :icon="faCompass" fixed-width />
                    Guided
                </BButton>
                <BButton
                    v-b-tooltip.hover.bottom.noninteractive
                    title="Advanced mode"
                    variant="link"
                    size="sm"
                    @click="openAdvancedMode">
                    <FontAwesomeIcon :icon="faSlidersH" fixed-width />
                    Advanced
                </BButton>
            </template>
            <template v-slot:header>
                <DelayedInput :delay="100" class="my-2" placeholder="Search upload methods" @change="query = $event" />
            </template>
            <ScrollList
                :item-key="(method) => method.id"
                :in-panel="true"
                name="upload method"
                name-plural="upload methods"
                load-disabled
                :prop-items="filteredMethods"
                :prop-total-count="allUploadMethods.length"
                :prop-busy="false">
                <template v-slot:item="{ item: method }">
                    <ButtonPlain
                        class="upload-method-item rounded p-3 mb-2"
                        :data-method-id="method.id"
                        @click="selectUploadMethod(method)">
                        <div class="d-flex align-items-start">
                            <div class="upload-method-icon mr-3">
                                <FontAwesomeIcon :icon="method.icon" size="2x" class="text-primary" />
                            </div>
                            <div class="text-left flex-grow-1">
                                <div class="upload-method-title font-weight-bold mb-1">
                                    {{ method.name }}
                                </div>
                                <div class="upload-method-description text-muted small">
                                    {{ method.description }}
                                </div>
                            </div>
                        </div>
                    </ButtonPlain>
                </template>
            </ScrollList>
        </ActivityPanel>

        <UploadMethodDialog :method-id="selectedMethod" :show.sync="showModal" @close="closeModal" />

        <GModal :show.sync="showGuidedModal" title="Guided Import Wizard" fullscreen>
            <div class="guided-wizard-content">
                <h4>TODO</h4>
                <p>This wizard will help you choose the best method to import your data into Galaxy.</p>
                <!-- TODO: Add wizard steps here -->
            </div>
        </GModal>

        <GModal :show.sync="showAdvancedModal" title="Advanced Import" fullscreen>
            <div class="advanced-import-content">
                <h4>TODO</h4>
                <p>Access all import options and advanced settings in one place.</p>
                <!-- TODO: Add advanced import interface here -->
            </div>
        </GModal>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.upload-panel-wrapper {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.upload-method-item {
    width: 100%;
    border: 1px solid $gray-300;
    transition: all 0.2s ease;
    background-color: white;

    &:hover {
        background-color: $gray-100;
        border-color: $brand-primary;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    &:active {
        transform: translateY(1px);
    }
}
</style>
