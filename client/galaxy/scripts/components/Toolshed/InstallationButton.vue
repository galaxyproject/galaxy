<template>
<div>
    <b-button v-if="installState"
        class="btn-sm"
        variant="primary"
        @click="onInstall">
        Install
    </b-button>
    <div v-else>
        <b-button v-if="uninstallState"
            class="btn-sm"
            variant="danger"
            @click="onUninstall">
            Uninstall
        </b-button>
        <b-button v-else
            class="btn-sm"
            @click="onUninstall">
            <span v-if="!errorState" class="fa fa-spinner fa-spin" />
            <span>{{ status }}</span>
        </b-button>
    </div>
</div>
</template>
<script>
export default {
    props: ["installed", "status"],
    computed: {
        installState() {
            return ["Uninstalled", ""].includes(this.status);
        },
        uninstallState() {
            return this.status == "Installed";
        },
        errorState() {
            return this.status == "Error";
        }
    },
    methods: {
        onInstall() {
            this.$emit("onInstall")
        },
        onUninstall() {
            this.$emit("onUninstall")
        }
    }
}
</script>
