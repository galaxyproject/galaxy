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

<script>
import { fetcher } from "schema/fetcher";
import LoadingSpan from "components/LoadingSpan";
import DescribeObjectStore from "components/ObjectStore/DescribeObjectStore";
import { errorMessageAsString } from "utils/simple-error";
import ObjectStoreBadges from "components/ObjectStore/ObjectStoreBadges";
import ProvidedQuotaSourceUsageBar from "components/User/DiskUsage/Quota/ProvidedQuotaSourceUsageBar";

export default {
    components: {
        LoadingSpan,
        DescribeObjectStore,
        ObjectStoreBadges,
        ProvidedQuotaSourceUsageBar,
    },
    props: {
        selectedObjectStoreId: {
            type: String,
            default: null,
        },
        defaultOptionTitle: {
            // "Use Your User Preference Defaults"
            type: String,
            required: true,
        },
        defaultOptionDescription: {
            // "Selecting this will cause the history to not set a default and to fallback to your user preference defined default."
            type: String,
            required: true,
        },
        forWhat: {
            type: String,
            required: true,
        },
        parentError: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            loading: true,
            error: this.parentError,
            popoverPlacement: "left",
            objectStores: [],
            loadingObjectStoreInfoMessage: "Loading object store information",
            galaxySelectionDefalutTitle: "Use Galaxy Defaults",
            galaxySelectionDefalutDescription:
                "Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator.",
            whyIsSelectionPreferredText: `
Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator.
Select a preferred object store for new datasets. This is should be thought of as a preferred
object store because depending the job and workflow configuration execution configuration of
this Galaxy instance - a different object store may be selected. After a dataset is created,
click on the info icon in the history panel to view information about where it is stored. If it
is not stored in the correct place, contact your Galaxy adminstrator for more information.
`,
        };
    },
    watch: {
        parentError() {
            this.error = this.parentError;
        },
    },
    async mounted() {
        const get = fetcher.path("/api/object_store").method("get").create();
        try {
            const { data } = await get({ selectable: true });
            this.objectStores = data;
            this.loading = false;
        } catch (e) {
            this.handleError(e);
        }
    },
    methods: {
        handleError(e) {
            const errorMessage = errorMessageAsString(e);
            this.error = errorMessage;
        },
        variant(objectStoreId) {
            if (this.selectedObjectStoreId == objectStoreId) {
                return "outline-primary";
            } else {
                return "outline-info";
            }
        },
        async handleSubmit(preferredObjectStoreId) {
            this.$emit("onSubmit", preferredObjectStoreId);
        },
    },
};
</script>
