<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import DescribeObjectStore from "@/components/ObjectStore/DescribeObjectStore.vue";
import { errorMessageAsString } from "@/utils/simple-error";
import ProvidedQuotaSourceUsageBar from "@/components/User/DiskUsage/Quota/ProvidedQuotaSourceUsageBar.vue";
import { getSelectableObjectStores } from "./services";

interface SelectObjectStoreProps {
    selectedObjectStoreId?: String | null;
    defaultOptionTitle: String;
    defaultOptionDescription: String;
    forWhat: string;
    parentError?: String | null;
}

const props = withDefaults(defineProps<SelectObjectStoreProps>(), {
    selectedObjectStoreId: null,
    parentError: null,
});

const loading = ref(true);
const error = ref(props.parentError);
const selected: any = ref(props.selectedObjectStoreId || "no_preference");
const objectStores = ref<Array<object>>([]);

const loadingObjectStoreInfoMessage = ref("Loading storage location information");
const whyIsSelectionPreferredText = ref(
    `Depending on the job and workflow execution configuration of this Galaxy a different storage location may be ultimately used. The order of priority is tool > workflow > history > user preferences > Galaxy administrator.`
);
const datasetInfoText = ref(
    `After a dataset is created, click on the info icon in the history panel to view information about where it is stored. If it is not stored in the place you want, contact Galaxy administrator for more information.`
);
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

const emit = defineEmits<{
    (e: "onSubmit", id: string | null): void;
    (e: "onCancel"): void;
}>();

async function handleSubmit() {
    let preferredObjectStoreId: string | null;
    if (selected.value === "no_preference") {
        preferredObjectStoreId = null;
    } else {
        preferredObjectStoreId = selected.value;
    }
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
                <b-col cols="4">
                    <b-form-group v-slot="{ ariaDescribedby }">
                        <b-form-radio-group
                            id="btn-radios-3"
                            v-model="selected"
                            :aria-describedby="ariaDescribedby"
                            name="radio-btn-stacked"
                            button-variant="outline-primary"
                            size="lg"
                            buttons
                            stacked>
                            <b-form-radio id="nopref" value="no_preference">{{ defaultOptionTitle }}</b-form-radio>
                            <b-form-radio
                                v-for="object_store in objectStores"
                                :key="object_store.object_store_id"
                                :value="object_store.object_store_id">
                                {{ object_store.name }}
                            </b-form-radio>
                        </b-form-radio-group>
                    </b-form-group>
                </b-col>
                <b-col cols="8">
                    <span v-show="selected === 'no_preference'">
                        <span v-localize>{{ defaultOptionDescription }}</span>
                    </span>
                    <span v-for="object_store in objectStores" :key="object_store.object_store_id">
                        <span v-show="selected === object_store.object_store_id">
                            <DescribeObjectStore :what="forWhat" :storage-info="object_store" />
                            <ProvidedQuotaSourceUsageBar :object-store="object_store" :compact="true" />
                        </span>
                    </span>
                </b-col>
            </b-row>
            <b-row>
                <b-col cols="12">
                    <p v-localize>
                        {{ whyIsSelectionPreferredText }}
                    </p>
                    <p>
                        {{ datasetInfoText }}
                    </p>
                </b-col>
            </b-row>
            <b-row class="modal-footer">
                <b-col cols="12">
                    <b-button title="Cancel" variant="secondary" @click="$emit('onCancel')"> Cancel </b-button>
                    <b-button title="Save" variant="primary" @click="handleSubmit"> Save </b-button>
                </b-col>
            </b-row>
        </div>
    </div>
</template>
