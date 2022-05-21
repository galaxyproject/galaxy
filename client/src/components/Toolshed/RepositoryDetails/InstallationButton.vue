<template>
    <div>
        <b-button v-if="installState" :class="buttonClass" variant="primary" @click="onInstall"> Install </b-button>
        <div v-else>
            <b-button v-if="uninstallState" :class="buttonClass" variant="danger" @click="onUninstall">
                Uninstall
            </b-button>
            <b-button v-else :class="buttonClass" variant="info" @click="onCancel">
                <span v-if="!errorState" class="fa fa-spinner fa-spin" />
                <span>{{ status }}</span>
            </b-button>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        status: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            buttonClass: "btn-sm text-nowrap",
        };
    },
    computed: {
        installState() {
            return !this.status || this.status == "Uninstalled";
        },
        uninstallState() {
            return this.status == "Installed";
        },
        errorState() {
            return this.status == "Error";
        },
    },
    methods: {
        onInstall() {
            this.$emit("onInstall");
        },
        onUninstall() {
            this.$emit("onUninstall");
        },
        onCancel() {
            if (window.confirm(`Do you want to reset this repository?`)) {
                this.$emit("onUninstall");
            }
        },
    },
};
</script>
