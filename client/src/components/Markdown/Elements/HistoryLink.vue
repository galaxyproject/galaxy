<template>
    <div>
        <b-link v-if="showLink" @click="onClick">Click to Import History: {{ name }}.</b-link>
        <div v-if="imported" class="text-success">
            <font-awesome-icon icon="check" class="mr-1" />
            <span>Successfully Imported History: {{ name }}!</span>
        </div>
        <div v-if="!!error" class="text-danger">
            <font-awesome-icon icon="exclamation-triangle" class="mr-1" />
            <span>Failed to Import History: {{ name }}!</span>
            <span>{{ error }}</span>
        </div>
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
        showLink() {
            return !this.imported && !this.error;
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
