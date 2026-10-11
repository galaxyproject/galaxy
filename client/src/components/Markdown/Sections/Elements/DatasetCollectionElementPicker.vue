<script setup lang="ts">
import { BFormSelect, BNavbar, BNavbarNav, BNavForm, BNavText } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { fetchCollectionElements, fetchCollectionSummary } from "@/api/datasetCollections";

interface CollectionElementPickerProps {
    hdcaId: string;
}
const props = defineProps<CollectionElementPickerProps>();
const dceToId = ref<{
    [k: string]: string | undefined;
}>();
const selectedValue = ref<string>();

watch(
    () => props.hdcaId,
    async () => {
        const collectionSummary = await fetchCollectionSummary({ hdca_id: props.hdcaId });
        const collectionElements = await fetchCollectionElements({
            hdcaId: props.hdcaId,
            collectionId: collectionSummary.collection_id,
            limit: 10,
        });
        const identifierAndIds = Object.fromEntries(
            collectionElements.map((element) => {
                return [element.object?.id, element.element_identifier];
            }),
        );
        dceToId.value = identifierAndIds;
    },
    { immediate: true },
);
const value = computed(() => selectedValue.value || Object.keys(dceToId.value || {}).at(0));

function handleInput(value: string) {
    selectedValue.value = value;
}
</script>

<template>
    <div>
        <BNavbar class="align-items-center">
            <div class="navbar-collapse">
                <BNavbarNav>
                    <BNavText class="mr-3">Select Element</BNavText>
                </BNavbarNav>
                <BNavForm>
                    <BFormSelect
                        class="form-control-sm"
                        :value="value"
                        :options="dceToId"
                        @input="handleInput"></BFormSelect>
                </BNavForm>
            </div>
        </BNavbar>
        <slot name="element" :element="value"></slot>
    </div>
</template>
