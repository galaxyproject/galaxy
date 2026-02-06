<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import type { CardBadge } from "@/components/Common/GCard.types";
import { useConfig } from "@/composables/config";
import { useUploadStagingCounts } from "@/composables/upload/useUploadStaging";

import type { UploadMethodConfig } from "./types";
import { useAllUploadMethods } from "./uploadMethodRegistry";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import GCard from "@/components/Common/GCard.vue";
import ScrollList from "@/components/ScrollList/ScrollList.vue";

interface Props {
    /** Whether this is displayed in a panel (affects ScrollList behavior) */
    inPanel?: boolean;
    /** Target selector for teleporting search input (for panel header) */
    searchTeleportTarget?: string;
}

const props = withDefaults(defineProps<Props>(), {
    inPanel: true,
    searchTeleportTarget: undefined,
});

const { config, isConfigLoaded } = useConfig();
const router = useRouter();
const query = ref("");

const searchInputClass = computed(() => (props.searchTeleportTarget ? "my-2" : props.inPanel ? "my-2" : "mb-3"));

const allUploadMethods = useAllUploadMethods();
const stagedCountsByMode = useUploadStagingCounts();

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

function updateQuery(newQuery: string) {
    query.value = newQuery;
}

function getStagingBadges(method: UploadMethodConfig): CardBadge[] {
    const count = stagedCountsByMode.value[method.id] ?? 0;
    if (count === 0) {
        return [];
    }
    return [
        {
            id: `staged-${method.id}`,
            label: String(count),
            title: `${count} upload item${count === 1 ? "" : "s"} staged and pending submission`,
            variant: "primary",
            type: "badge",
        },
    ];
}
</script>

<template>
    <div class="upload-method-list-wrapper h-100 d-flex flex-column">
        <Teleport :to="searchTeleportTarget" :disabled="!searchTeleportTarget">
            <DelayedInput
                :delay="100"
                :class="searchInputClass"
                placeholder="Search import methods..."
                @change="updateQuery" />
        </Teleport>

        <div class="flex-grow-1 overflow-hidden">
            <ScrollList
                :item-key="(method) => method.id"
                :in-panel="inPanel"
                name="import method"
                name-plural="import methods"
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
                        :badges="getStagingBadges(method)"
                        :data-method-id="method.id"
                        @click="selectUploadMethod(method)" />
                </template>
            </ScrollList>
        </div>
    </div>
</template>
