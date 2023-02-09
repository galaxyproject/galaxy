<template>
    <SelectObjectStore
        :root="root"
        :for-what="newDatasetsDescription"
        :selected-object-store-id="selectedObjectStoreId"
        :default-option-title="defaultOptionTitle"
        :default-option-description="defaultOptionDescription"
        @onSubmit="handleSubmit" />
</template>
<script>
import SelectObjectStore from "components/ObjectStore/SelectObjectStore";

export default {
    components: {
        SelectObjectStore,
    },
    props: {
        root: {
            type: String,
            required: true,
        },
        toolPreferredObjectStoreId: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            selectedObjectStoreId: this.toolPreferredObjectStoreId,
            newDatasetsDescription: "The default object store for the outputs of this tool",
        };
    },
    computed: {
        defaultOptionTitle() {
            return "Use Defaults";
        },
        defaultOptionDescription() {
            return "If the history has a default set, that will be used. If instead, you've set an option in your user preferences - that will be assumed to be your default selection. Finally, the Galaxy configuration will be used.";
        },
    },
    methods: {
        async handleSubmit(preferredObjectStoreId) {
            this.selectedObjectStoreId = preferredObjectStoreId;
            this.$emit("updated", preferredObjectStoreId);
        },
    },
};
</script>
