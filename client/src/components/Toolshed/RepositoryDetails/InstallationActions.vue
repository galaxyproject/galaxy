<template>
    <div>
        <span class="d-inline-block status">
            <span v-if="installingState" class="fa fa-spinner fa-spin" />
            {{ status }}
        </span>
        <div class="d-inline-block">
            <b-button
                :disabled="!installState"
                :class="buttonClass"
                :variant="installState ? 'primary' : ''"
                @click="onInstall">
                Install
            </b-button>
            <b-button
                :disabled="!uninstallState"
                :class="buttonClass"
                :variant="uninstallState ? 'danger' : ''"
                @click="onUninstall">
                Uninstall
            </b-button>
            <b-button
                :disabled="!resetState"
                :class="buttonClass"
                :title="l('Reset Broken or Stuck Installation')"
                :variant="resetState ? 'warning' : ''"
                @click="onCancel">
                Reset
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
            default: "Uninstalled",
        },
    },
    data() {
        return {
            buttonClass: "btn-sm text-nowrap",
        };
    },
    computed: {
        installState() {
            return !this.status || this.status === "Uninstalled";
        },
        uninstallState() {
            return this.status === "Installed";
        },
        resetState() {
            return !this.installState && !this.uninstallState;
        },
        installingState() {
            return this.status !== "Error" && this.resetState;
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

<style lang="scss" scoped>
.status {
    display: inline-block;
    min-width: 80px;
}
</style>
