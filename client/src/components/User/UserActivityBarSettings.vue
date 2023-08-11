<script setup lang="ts">
import { computed, type Ref, ref, type WritableComputedRef } from "vue";

import { GCard, GFormCheckbox } from "@/component-library";
import { useUserStore } from "@/stores/userStore";

const userStore = useUserStore();

const show: Ref<Boolean> = ref(false);

const enableActivityBar: WritableComputedRef<Boolean> = computed({
    get: () => {
        return userStore.showActivityBar;
    },
    set: () => {
        // always toggle tool side panel when enabling activity bar
        if (userStore.toggledSideBar !== "tools") {
            userStore.toggleSideBar("tools");
        }
        // toggle activity bar
        userStore.toggleActivityBar();
    },
});
</script>

<template>
    <GCard :show="show" class="user-activity-bar-settings mr-3">
        <GFormCheckbox v-model="enableActivityBar" switch>
            <b>Enable Activity Bar</b>
        </GFormCheckbox>
    </GCard>
</template>
