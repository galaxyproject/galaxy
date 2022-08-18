<script setup>
import { computed } from "vue";

const props = defineProps({
    status: String,
});

const installState = computed(() => !props.status || props.status === "Uninstalled");
const uninstallState = computed(() => props.status === "Installed");

const emit = defineEmits(["onInstall", "onUninstall"]);

function onCancel() {
    if (window.confirm(`Do you want to reset this repository?`)) {
        emit("onUninstall");
    }
}
</script>

<template>
    <div>
        <b-button v-if="installState" variant="primary" class="btn-sm" @click="() => emit('onInstall')">
            Install
        </b-button>
        <b-button v-else-if="uninstallState" variant="danger" class="btn-sm" @click="() => emit('onUninstall')">
            Uninstall
        </b-button>
        <b-button
            v-else
            variant="warning"
            class="btn-sm"
            :title="l('Reset Broken or Stuck Installation')"
            @click="onCancel">
            Reset
        </b-button>
    </div>
</template>

<style lang="scss" scoped>
button {
    min-width: 80px;
}
</style>
