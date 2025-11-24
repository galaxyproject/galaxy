<script setup lang="ts">
import { faCompass, faSlidersH } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";

import type { UploadMethodConfig } from "./types";
import { getAllUploadMethods } from "./uploadMethodRegistry";
import { useUploadState } from "./uploadState";

import UploadProgressDisplay from "./UploadProgressDisplay.vue";
import UploadProgressIndicator from "./UploadProgressIndicator.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

const { config, isConfigLoaded } = useConfig();
const { activeItems } = useUploadState();

const router = useRouter();
const query = ref("");
const showUploadDetailsModal = ref(false);
const showGuidedModal = ref(false);
const showAdvancedModal = ref(false);

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
    router.push(`/upload/${method.id}`);
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
                <UploadProgressIndicator :uploads="activeItems" @show-details="showUploadDetailsModal = true" />
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

        <GModal :show.sync="showUploadDetailsModal" title="Upload Status" size="medium" fixed-height>
            <div class="upload-details-modal">
                <template v-if="activeItems.length > 0">
                    <div class="modal-summary mb-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>Uploads</strong>
                                <span class="text-muted ml-2">
                                    {{ activeItems.filter((i) => i.status === "completed").length }}/{{
                                        activeItems.length
                                    }}
                                    files completed
                                </span>
                            </div>
                            <div class="text-muted small">
                                <span
                                    v-if="
                                        activeItems.some((i) => i.status === 'uploading' || i.status === 'processing')
                                    ">
                                    {{ activeItems.filter((i) => i.status === "error").length }} error(s)
                                </span>
                            </div>
                        </div>
                    </div>
                    <UploadProgressDisplay :uploads="activeItems" />
                </template>
                <div v-else class="d-flex flex-column align-items-center justify-content-center h-100 text-muted">
                    <p class="lead mb-2">No uploads in progress.</p>
                    <p class="small mb-3">Start a new upload using the Upload Activity.</p>
                </div>
            </div>
        </GModal>

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
