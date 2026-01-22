<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";
import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";

import type { UploadMethodConfig } from "./types";
import { useAllUploadMethods } from "./uploadMethodRegistry";
import { useUploadState } from "./uploadState";

import UploadProgressIndicator from "./UploadProgressIndicator.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import GCard from "@/components/Common/GCard.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

const { config, isConfigLoaded } = useConfig();
const { hasUploads } = useUploadState();
const { advancedMode } = useUploadAdvancedMode();

const router = useRouter();
const query = ref("");

const allUploadMethods = useAllUploadMethods();

const availableMethods = computed(() => {
    if (!isConfigLoaded.value) {
        return allUploadMethods.value;
    }

    return allUploadMethods.value.filter((method: UploadMethodConfig) => {
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
    return availableMethods.value.filter((method: UploadMethodConfig) => {
        const searchText = `${method.name} ${method.description}`.toLowerCase();
        return tokens.every((token) => searchText.includes(token));
    });
});

function selectUploadMethod(method: UploadMethodConfig) {
    router.push(`/upload/${method.id}`);
}

function showProgressDetails() {
    router.push("/upload/progress");
}
</script>

<template>
    <div class="upload-panel-wrapper">
        <ActivityPanel title="Import Data" data-description="beta upload panel">
            <template v-slot:header-buttons>
                <BFormCheckbox
                    v-model="advancedMode"
                    v-b-tooltip.hover.noninteractive
                    size="sm"
                    switch
                    class="mr-2"
                    title="Show advanced upload options">
                    <span class="small">Advanced</span>
                </BFormCheckbox>
            </template>
            <template v-slot:header>
                <UploadProgressIndicator v-if="hasUploads" @show-details="showProgressDetails" />
                <DelayedInput :delay="100" class="my-2" placeholder="Search upload methods" @change="query = $event" />
            </template>
            <ScrollList
                :item-key="(method) => method.id"
                :in-panel="true"
                name="upload method"
                name-plural="upload methods"
                load-disabled
                :prop-items="filteredMethods"
                :prop-total-count="filteredMethods.length"
                :prop-busy="false">
                <template v-slot:item="{ item: method }">
                    <GCard
                        clickable
                        container-class="mb-2"
                        :title="method.name"
                        title-size="text"
                        :full-description="true"
                        :description="method.description"
                        :title-icon="{ icon: method.icon, class: 'text-primary', size: 'lg' }"
                        :data-method-id="method.id"
                        @click="selectUploadMethod(method)" />
                </template>
            </ScrollList>
        </ActivityPanel>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.upload-panel-wrapper {
    height: 100%;
    display: flex;
    flex-direction: column;
}
</style>
