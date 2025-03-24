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
    if (window.confirm(`您确定要重置此仓库吗？`)) {
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
            安装
        </b-button>
        <b-button v-else-if="uninstallState" variant="danger" class="btn-sm" @click="() => emit('onUninstall')">
            卸载
        </b-button>
        <b-button
            v-else
            variant="warning"
            class="btn-sm"
            :title="localize('重置损坏或卡住的安装')"
            @click="onReset">
            重置
        </b-button>
    </div>
</template>

<style lang="scss" scoped>
button {
    min-width: 80px;
}
</style>
