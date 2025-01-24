<script setup lang="ts">
import { BPopover } from "bootstrap-vue";

import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";

defineProps<{
    title: string;
    target: string;
}>();

const userStore = useUserStore();
</script>

<template>
    <BPopover v-if="userStore.isAnonymous" :target="target" triggers="hover focus" placement="bottom">
        <template v-slot:title> {{ title }} </template>
        Please <a :href="withPrefix('/login')">log in or register</a> to use this feature.
    </BPopover>
</template>
