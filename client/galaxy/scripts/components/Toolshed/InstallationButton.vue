<template>
    <div>
        <b-button v-if="installState" :class="buttonClass" variant="primary" @click="onInstall">
            Install
        </b-button>
        <div v-else>
            <b-button v-if="uninstallState" :class="buttonClass" variant="danger" @click="onUninstall">
                Uninstall
            </b-button>
            <b-button v-else :class="buttonClass" @click="onUninstall">
                <span v-if="!errorState" class="fa fa-spinner fa-spin" />
                <span>{{ status }}</span>
            </b-button>
        </div>
    </div>
</template>
<script>
export default {
    props: ["installed", "status"],
    data() {
        return {
            buttonClass: "btn-sm text-nowrap"
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
        }
    },
    methods: {
        onInstall() {
            this.$emit("onInstall");
        },
        onUninstall() {
            this.$emit("onUninstall");
        }
    }
};
</script>
