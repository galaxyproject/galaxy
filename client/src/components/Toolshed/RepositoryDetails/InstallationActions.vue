<script setup lang="ts">
import { computed } from "vue";

import localize from "@/utils/localization";

interface Props {
    status?: string;
    isBusy?: boolean;
}

const props = defineProps<Props>();

const installState = computed(() => !props.status || props.status === "Uninstalled");
const uninstallState = computed(() => props.status === "Installed");

const emit = defineEmits(["onInstall", "onUninstall", "onReset"]);

function onReset() {
    if (window.confirm(`Do you want to reset this repository?`)) {
        emit("onReset");
    }
}
</script>

<template>
    <div>
        <b-button v-if="isBusy" variant="secondary" class="btn-sm" disabled>
            <b-spinner small></b-spinner>
        </b-button>
        <b-button v-else-if="installState" variant="primary" class="btn-sm" @click="() => emit('onInstall')">
            Install
        </b-button>
        <b-button v-else-if="uninstallState" variant="danger" class="btn-sm" @click="() => emit('onUninstall')">
            Uninstall
        </b-button>
        <b-button
            v-else
            variant="warning"
            class="btn-sm"
            :title="localize('Reset Broken or Stuck Installation')"
            @click="onReset">
            Reset
        </b-button>
    </div>
</template>

<style lang="scss" scoped>
button {
    min-width: 80px;
}
</style>
