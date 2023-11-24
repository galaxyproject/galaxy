<script setup lang="ts">
import { computed, ref, type WritableComputedRef, type Ref } from "vue";
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
    <b-card :show="show" class="user-activity-bar-settings mr-3">
        <b-form-checkbox v-model="enableActivityBar" switch>
            <b>Enable Activity Bar</b>
        </b-form-checkbox>
    </b-card>
</template>
