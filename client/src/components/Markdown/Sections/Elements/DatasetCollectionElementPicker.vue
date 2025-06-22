<script setup lang="ts">
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
            })
        );
        dceToId.value = identifierAndIds;
    },
    { immediate: true }
);
const value = computed(() => selectedValue.value || Object.keys(dceToId.value || {}).at(0));

function handleInput(value: string) {
    selectedValue.value = value;
}
</script>

<template>
    <div>
        <b-navbar class="align-items-center">
            <b-collapse id="nav-text-collapse" is-nav>
                <b-navbar-nav>
                    <b-nav-text class="mr-3">Select Element</b-nav-text>
                </b-navbar-nav>
                <b-nav-form>
                    <b-form-select
                        class="form-control-sm"
                        :value="value"
                        :options="dceToId"
                        @input="handleInput"></b-form-select>
                </b-nav-form>
            </b-collapse>
        </b-navbar>
        <slot name="element" :element="value"></slot>
    </div>
</template>
