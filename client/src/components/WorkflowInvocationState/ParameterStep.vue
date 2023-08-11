<template>
    <GTable :fields="['label', 'parameter_value']" :items="parameters" caption-top small />
</template>
<script>
import { GTable } from "@/component-library";

export default {
    components: {
        GTable,
    },
    props: {
        parameters: { type: Array, required: true },
    },
};
</script>
