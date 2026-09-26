<script setup lang="ts">
import { computed } from "vue";

import localize from "@/utils/localization";

import GButton from "@/components/BaseComponents/GButton.vue";

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
        <GButton v-if="isBusy" size="small" disabled>
            <b-spinner small></b-spinner>
        </GButton>
        <GButton v-else-if="installState" color="blue" size="small" @click="() => emit('onInstall')"> Install </GButton>
        <GButton v-else-if="uninstallState" color="red" size="small" @click="() => emit('onUninstall')">
            Uninstall
        </GButton>
        <GButton
            v-else
            color="yellow"
            size="small"
            :title="localize('Reset Broken or Stuck Installation')"
            @click="onReset">
            Reset
        </GButton>
    </div>
</template>

<style lang="scss" scoped>
button {
    min-width: 80px;
}
</style>
