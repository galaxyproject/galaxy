<template>
    <SelectObjectStore
        :parent-error="error"
        :for-what="newDatasetsDescription"
        :selected-object-store-id="selectedObjectStoreId"
        :default-option-title="defaultOptionTitle"
        :default-option-description="defaultOptionDescription"
        @onSubmit="handleSubmit" />
</template>

<script>
import axios from "axios";
import SelectObjectStore from "components/ObjectStore/SelectObjectStore";
import { prependPath } from "utils/redirect";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: {
        SelectObjectStore,
    },
    props: {
        userPreferredObjectStoreId: {
            type: String,
            default: null,
        },
        history: {
            type: Object,
            required: true,
        },
    },
    data() {
        const selectedObjectStoreId = this.history.preferred_object_store_id;
        return {
            error: null,
            selectedObjectStoreId: selectedObjectStoreId,
            newDatasetsDescription: "New dataset outputs from tools and workflows executed in this history",
            popoverPlacement: "left",
            galaxySelectionDefaultTitle: "Use Galaxy Defaults",
            galaxySelectionDefaultDescription:
                "Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator.",
            userSelectionDefaultTitle: "Use Your User Preference Defaults",
            userSelectionDefaultDescription:
                "Selecting this will cause the history to not set a default and to fallback to your user preference defined default.",
        };
    },
    computed: {
        defaultOptionTitle() {
            if (this.userPreferredObjectStoreId) {
                return this.userSelectionDefaultTitle;
            } else {
                return this.galaxySelectionDefaultTitle;
            }
        },
        defaultOptionDescription() {
            if (this.userPreferredObjectStoreId) {
                return this.userSelectionDefaultDescription;
            } else {
                return this.galaxySelectionDefaultDescription;
            }
        },
    },
    methods: {
        async handleSubmit(preferredObjectStoreId) {
            const payload = { preferred_object_store_id: preferredObjectStoreId };
            const url = prependPath(`api/histories/${this.history.id}`);
            try {
                await axios.put(url, payload);
            } catch (e) {
                this.error = errorMessageAsString(e);
            }
            this.selectedObjectStoreId = preferredObjectStoreId;
            this.$emit("updated", preferredObjectStoreId);
        },
    },
};
</script>
