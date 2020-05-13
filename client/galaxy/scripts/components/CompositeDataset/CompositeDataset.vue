<template>
    <div>
        <CompositeDatasetFile v-if="path" v-bind="$props"/>
        <CompositeDatasetDirectory v-else
                                   :history_dataset_id="history_dataset_id"
                                   :label="label"
        />
    </div>
</template>

<script>
    import CompositeDatasetFile from "./CompositeDatasetFile"
    import CompositeDatasetDirectory from "./CompositeDatasetDirectory"

    export default {
        props: {
            history_dataset_id: {
                type: String,
                required: true,
            },
            path: {
                type: String,
            },
            label: {
                type: String,
            },
        },
        components: {
            CompositeDatasetFile,
            CompositeDatasetDirectory
        }
    };
</script>
