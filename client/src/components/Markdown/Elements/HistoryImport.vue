<template>
    <div>
        <b-link @click="onClick" class="mr-2">Click to import History: {{ name }}.</b-link>
        <span v-if="imported" class="text-success">
            <font-awesome-icon icon="check" class="mr-1" />
            <span>Successfully Imported History!</span>
        </span>
        <span v-if="!!error" class="text-danger">
            <font-awesome-icon icon="exclamation-triangle" class="mr-1" />
            <span>Failed to Import History!</span>
            <span>{{ error }}</span>
        </span>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { errorMessageAsString } from "utils/simple-error";

Vue.use(BootstrapVue);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        args: {
            type: Object,
            default: null,
        },
        histories: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            imported: false,
            error: false,
        };
    },
    computed: {
        name() {
            return this.histories[this.args.history_id].name;
        },
    },
    methods: {
        onClick() {
            axios
                .post(`${getAppRoot()}api/histories`, { history_id: this.args.history_id })
                .then(() => {
                    this.imported = true;
                })
                .catch((e) => {
                    this.error = errorMessageAsString(e);
                });
        },
    },
};
</script>
