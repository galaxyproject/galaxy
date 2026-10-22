<script setup lang="ts">
import { BCard, BCardTitle } from "bootstrap-vue";
import { ref } from "vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import type { WhichListBuilder } from "./types";

import GButton from "@/components/BaseComponents/GButton.vue";
import CollectionTypeCards from "@/components/Collections/common/CollectionTypeCards.vue";

interface Props {
    value: WhichListBuilder;
    initialAdvanced: boolean;
}

const emit = defineEmits(["onChange"]);

const props = defineProps<Props>();

const advanced = ref(props.initialAdvanced);

function toggleAdvanced() {
    advanced.value = !advanced.value;
}
</script>

<template>
    <div class="w-100">
        <CollectionTypeCards
            :value="value"
            :types="['list', 'list:paired']"
            context="builder"
            hide-type
            @select="emit('onChange', $event)">
            <template v-slot:extra>
                <BCard
                    data-which-builder="rules"
                    class="wizard-selection-card"
                    :border-variant="borderVariant(value === 'rules')"
                    role="button"
                    tabindex="0"
                    @click="emit('onChange', 'rules')"
                    @keydown.enter="emit('onChange', 'rules')"
                    @keydown.space.prevent="emit('onChange', 'rules')">
                    <BCardTitle title-tag="h4" class="h-sm mb-1">
                        <b>Rule Builder</b>
                    </BCardTitle>
                    <div class="mt-3">
                        The rule builder allows building arbitrarily nested collections of data with reproducible
                        metadata parsing and other advanced features.
                    </div>
                </BCard>
            </template>
        </CollectionTypeCards>
        <div v-if="!advanced" class="m-3">
            <GButton color="blue" @click="toggleAdvanced">Advanced Options</GButton>
        </div>
        <CollectionTypeCards
            v-else
            class="mt-3"
            :value="value"
            :types="['list:paired_or_unpaired', 'list:list', 'list:list:paired']"
            context="builder"
            hide-type
            @select="emit('onChange', $event)" />
    </div>
</template>
