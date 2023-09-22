<template>
    <pre><code class="word-wrap-normal">{{ content }}</code></pre>
</template>

<script>
const ATTRIBUTES = {
    history_dataset_name: "name",
    history_dataset_info: "info",
    history_dataset_peek: "peek",
    history_dataset_type: "ext",
};
export default {
    props: {
        args: {
            type: Object,
            required: true,
        },
        datasets: {
            type: Object,
            default: null,
        },
        name: {
            type: String,
            default: null,
        },
    },
    computed: {
        getClass() {
            return `dataset-${ATTRIBUTES[this.name]}`;
        },
        content() {
            const dataset = this.datasets[this.args.history_dataset_id];
            return dataset && dataset[ATTRIBUTES[this.name]];
        },
    },
};
</script>
