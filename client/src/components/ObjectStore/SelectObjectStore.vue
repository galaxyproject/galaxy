<script lang="ts" setup>
import { ref, watch, onMounted } from "vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";
import { errorMessageAsString } from "@/utils/simple-error";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";
import ProvidedQuotaSourceUsageBar from "@/components/User/DiskUsage/Quota/ProvidedQuotaSourceUsageBar.vue";
import { getSelectableObjectStores } from "./services";

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

const loading = ref(true);
const error = ref(props.parentError);
const popoverPlacement = "left";
const objectStores = ref<Array<object>>([]);

const loadingObjectStoreInfoMessage = ref("Loading object store information");
const whyIsSelectionPreferredText = ref(`
Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator.
Select a preferred object store for new datasets. This is should be thought of as a preferred
object store because depending the job and workflow configuration execution configuration of
this Galaxy instance - a different object store may be selected. After a dataset is created,
click on the info icon in the history panel to view information about where it is stored. If it
is not stored in the correct place, contact your Galaxy administrator for more information.
`);

watch(
    () => props.parentError,
    () => {
        error.value = props.parentError;
    }
);

function handleError(e: unknown) {
    const errorMessage = errorMessageAsString(e);
    error.value = errorMessage;
}

onMounted(async () => {
    try {
        const data = await getSelectableObjectStores();
        objectStores.value = data;
        loading.value = false;
    } catch (e) {
        handleError(e);
    }
});

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

async function handleSubmit(preferredObjectStoreId: string) {
    emit("onSubmit", preferredObjectStoreId);
}
</script>

<template>
    <div>
        <loading-span v-if="loading" :message="loadingObjectStoreInfoMessage" />
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
                        <b-button
                            v-for="object_store in objectStores"
                            :id="`preferred-object-store-button-${object_store.object_store_id}`"
                            :key="object_store.object_store_id"
                            :variant="variant(object_store.object_store_id)"
                            class="preferred-object-store-select-button"
                            :data-object-store-id="object_store.object_store_id"
                            @click="handleSubmit(object_store.object_store_id)"
                            >{{ object_store.name }}
                            <ObjectStoreBadges :badges="object_store.badges" size="lg" :more-on-hover="false" />
                            <ProvidedQuotaSourceUsageBar :object-store="object_store" :compact="true">
                            </ProvidedQuotaSourceUsageBar>
                        </b-button>
                    </b-button-group>
                </b-col>
                <b-col cols="5">
                    <p v-localize style="float: right">
                        {{ whyIsSelectionPreferredText }}
                    </p>
                </b-col>
            </b-row>
            <b-popover target="no-preferred-object-store-button" triggers="hover" :placement="popoverPlacement">
                <template v-slot:title
                    ><span v-localize>{{ defaultOptionTitle }}</span></template
                >
                <span v-localize>{{ defaultOptionDescription }}</span>
            </b-popover>
            <b-popover
                v-for="object_store in objectStores"
                :key="object_store.object_store_id"
                :target="`preferred-object-store-button-${object_store.object_store_id}`"
                triggers="hover"
                :placement="popoverPlacement">
                <template v-slot:title>{{ object_store.name }}</template>
                <DescribeObjectStore :what="forWhat" :storage-info="object_store"> </DescribeObjectStore>
            </b-popover>
        </div>
    </div>
</template>
