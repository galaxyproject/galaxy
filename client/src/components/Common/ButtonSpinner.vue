<template>
    <b-button v-if="wait" variant="info" disabled>
        <font-awesome-icon icon="spinner" class="mr-2" spin />Please wait...
    </b-button>
    <b-button v-else variant="primary" @click="$emit('onClick')">
        <font-awesome-icon icon="check" class="mr-2" />{{ title }}
    </b-button>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faSpinner } from "@fortawesome/free-solid-svg-icons";

Vue.use(BootstrapVue);

library.add(faCheck);
library.add(faSpinner);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        title: {
            type: String,
            required: true,
        },
        wait: {
            type: Boolean,
            default: false,
        },
    },
};
</script>
