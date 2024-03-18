<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { ConcreteObjectStoreModel } from "@/api";
import { useObjectStoreStore } from "@/stores/objectStoreStore";

import ObjectStoreSelectButton from "./ObjectStoreSelectButton.vue";
import ObjectStoreSelectButtonDescribePopover from "./ObjectStoreSelectButtonDescribePopover.vue";
import ObjectStoreSelectButtonPopover from "./ObjectStoreSelectButtonPopover.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

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
    (e: "onSubmit", id: string | null, isPrivate: boolean): void;
}>();

const error = computed(() => {
    return props.parentError || loadErrorMessage.value;
});

async function handleSubmit(preferredObjectStore: ConcreteObjectStoreModel | null) {
    const id: string | null = (preferredObjectStore ? preferredObjectStore.object_store_id : null) as string | null;
    const isPrivate: boolean = preferredObjectStore ? preferredObjectStore.private : false;
    emit("onSubmit", id, isPrivate);
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
                            :key="objectStore.object_store_id"
                            id-prefix="preferred"
                            :object-store="objectStore"
                            :variant="variant(objectStore.object_store_id)"
                            class="preferred-object-store-select-button"
                            @click="handleSubmit(objectStore)" />
                    </b-button-group>
                </b-col>
                <b-col cols="5">
                    <p v-localize style="float: right">
                        {{ whyIsSelectionPreferredText }}
                    </p>
                </b-col>
            </b-row>
            <ObjectStoreSelectButtonPopover target="no-preferred-object-store-button" :title="defaultOptionTitle">
                <span v-localize>{{ defaultOptionDescription }}</span>
            </ObjectStoreSelectButtonPopover>
            <ObjectStoreSelectButtonDescribePopover
                v-for="objectStore in selectableObjectStores"
                :key="objectStore.object_store_id"
                id-prefix="preferred"
                :what="forWhat"
                :object-store="objectStore">
            </ObjectStoreSelectButtonDescribePopover>
        </div>
    </div>
</template>
