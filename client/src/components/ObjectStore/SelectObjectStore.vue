<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { useObjectStoreStore } from "@/stores/objectStoreStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";
import ObjectStoreSelectButton from "./ObjectStoreSelectButton.vue";

interface SelectObjectStoreProps {
    selectedObjectStoreId?: String | null;
    defaultOptionTitle: String;
    defaultOptionDescription: String;
    forWhat: String;
    parentError?: String | null;
}

const props = withDefaults(defineProps<SelectObjectStoreProps>(), {
    selectedObjectStoreId: null,
    parentError: null,
});

const popoverProps = {
    placement: "rightbottom",
    boundary: "window", // don't warp the popover to squeeze it into this modal
};

const store = useObjectStoreStore();
const { isLoading, loadErrorMessage, selectableObjectStores } = storeToRefs(store);

const loadingObjectStoreInfoMessage = ref("Loading object store information");
const whyIsSelectionPreferredText = ref(`
Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator.
Select a preferred object store for new datasets. This is should be thought of as a preferred
object store because depending the job and workflow configuration execution configuration of
this Galaxy instance - a different object store may be selected. After a dataset is created,
click on the info icon in the history panel to view information about where it is stored. If it
is not stored in the correct place, contact your Galaxy administrator for more information.
`);

function variant(objectStoreId: string) {
    if (props.selectedObjectStoreId == objectStoreId) {
        return "outline-primary";
    } else {
        return "outline-info";
    }
}

const emit = defineEmits<{
    (e: "onSubmit", id: string | null): void;
}>();

const error = computed(() => {
    return props.parentError || loadErrorMessage.value;
});

async function handleSubmit(preferredObjectStoreId: string) {
    emit("onSubmit", preferredObjectStoreId);
}
</script>

<template>
    <div>
        <LoadingSpan v-if="isLoading" :message="loadingObjectStoreInfoMessage" />
        <div v-else>
            <b-alert v-if="error" variant="danger" class="object-store-selection-error" show>
                {{ error }}
            </b-alert>
            <b-row>
                <b-col cols="7">
                    <b-button-group vertical size="lg" style="width: 100%">
                        <b-button
                            id="no-preferred-object-store-button"
                            :variant="variant(null)"
                            class="preferred-object-store-select-button"
                            data-object-store-id="__null__"
                            @click="handleSubmit(null)"
                            ><i>{{ defaultOptionTitle | localize }}</i></b-button
                        >
                        <ObjectStoreSelectButton
                            v-for="objectStore in selectableObjectStores"
                            :id="`preferred-object-store-button-${objectStore.object_store_id}`"
                            :key="objectStore.object_store_id"
                            :object-store="objectStore"
                            :variant="variant(objectStore.object_store_id)"
                            class="preferred-object-store-select-button"
                            @click="handleSubmit(objectStore.object_store_id)" />
                    </b-button-group>
                </b-col>
                <b-col cols="5">
                    <p v-localize style="float: right">
                        {{ whyIsSelectionPreferredText }}
                    </p>
                </b-col>
            </b-row>
            <b-popover target="no-preferred-object-store-button" triggers="hover" v-bind="popoverProps">
                <template v-slot:title
                    ><span v-localize>{{ defaultOptionTitle }}</span></template
                >
                <span v-localize>{{ defaultOptionDescription }}</span>
            </b-popover>
            <b-popover
                v-for="object_store in selectableObjectStores"
                :key="object_store.object_store_id"
                :target="`preferred-object-store-button-${object_store.object_store_id}`"
                triggers="hover"
                v-bind="popoverProps">
                <template v-slot:title>{{ object_store.name }}</template>
                <DescribeObjectStore :what="forWhat" :storage-info="object_store"> </DescribeObjectStore>
            </b-popover>
        </div>
    </div>
</template>
