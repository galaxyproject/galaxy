<template>
    <b-form-input v-bind="$attrs" v-on="$listeners"> </b-form-input>
</template>

<script>
import { BFormInput } from "bootstrap-vue";

export default {
    components: {
        BFormInput,
    },
};
</script>
