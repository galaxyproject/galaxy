<script setup>
import { computed } from "vue";

const props = defineProps({
    status: String,
});

const emit = defineEmits(["onInstall", "onUninstall"]);

const buttonClass = "btn-sm text-nowrap";

const installState = computed(() => !props.status || props.status === "Uninstalled");
const uninstallState = computed(() => props.status === "Installed");

function onCancel() {
    if (window.confirm(`Do you want to reset this repository?`)) {
        emit("onUninstall");
    }
}
</script>

<template>
    <div>
        <div class="d-inline-block">
            <b-button v-if="installState" variant="primary" :class="buttonClass" @click="() => emit('onInstall')">
                Install
            </b-button>
            <b-button
                v-else-if="uninstallState"
                variant="danger"
                :class="buttonClass"
                @click="() => emit('onUninstall')">
                Uninstall
            </b-button>
            <b-button
                v-else
                variant="warning"
                :class="buttonClass"
                :title="l('Reset Broken or Stuck Installation')"
                @click="onCancel">
                Reset
            </b-button>
        </div>
    </div>
</template>

<style lang="scss" scoped>
button {
    min-width: 80px;
}
</style>
