<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import { useConfig } from "@/composables/config";

import type { UploadMethodConfig } from "./types";
import { useAllUploadMethods } from "./uploadMethodRegistry";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";

const router = useRouter();

const { config, isConfigLoaded } = useConfig();

const query = ref("");

const allUploadMethods = useAllUploadMethods();

const breadcrumbItems = [{ title: "Import Data" }];

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
</script>

<template>
    <div class="upload-index h-100 d-flex flex-column">
        <BreadcrumbHeading :items="breadcrumbItems" />

        <div class="upload-index-content flex-grow-1 overflow-auto p-3">
            <div class="mb-3">
                <h2 class="h-lg mb-2">Choose an Import Method</h2>
                <p class="text-muted">Select how you want to import data into Galaxy</p>
            </div>

            <DelayedInput :delay="100" class="mb-3" placeholder="Search import methods..." @change="query = $event" />

            <div class="upload-methods-grid">
                <ButtonPlain
                    v-for="method in filteredMethods"
                    :key="method.id"
                    class="upload-method-card"
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
            </div>

            <div v-if="filteredMethods.length === 0" class="text-center text-muted py-5">
                <p>No import methods found matching your search.</p>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.upload-index {
    background-color: $white;
}

.upload-methods-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1rem;
}

.upload-method-card {
    width: 100%;
    border: 1px solid $border-color;
    border-radius: $border-radius-base;
    padding: 1.25rem;
    transition: all 0.2s ease;
    background-color: $white;
    text-decoration: none;

    &:hover {
        background-color: $gray-100;
        border-color: $brand-primary;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }

    &:active {
        transform: translateY(0);
    }
}

.upload-method-icon {
    flex-shrink: 0;
}

.upload-method-title {
    color: $text-color;
    font-size: 1.1rem;
}

.upload-method-description {
    line-height: 1.4;
}
</style>
