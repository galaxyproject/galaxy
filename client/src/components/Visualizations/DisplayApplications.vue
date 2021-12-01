<template>
    <div>
        {{ datasetId }}
    </div>
</template>
<script>
export default {
    props: {
        datasetId: {
            type: String,
            required: true,
        },
    },
};
</script>
