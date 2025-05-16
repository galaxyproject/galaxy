<script setup lang="ts">
import { onMounted, ref } from "vue";

import { useUserStore } from "@/stores/userStore";
import { withPrefix } from "@/utils/redirect";

import Popper from "@/components/Popper/Popper.vue";

const props = defineProps<{
    title: string;
    target: string;
}>();

const userStore = useUserStore();
const referenceEl = ref<HTMLElement | null>(null);

onMounted(() => {
    referenceEl.value = document.querySelector(`#${props.target}`) as HTMLElement | null;
});
</script>

<template>
    <Popper
        v-if="userStore.isAnonymous && referenceEl"
        placement="bottom"
        mode="light"
        :interactive="true"
        :reference-el="referenceEl">
        <div class="py-1 px-2 bg-primary rounded-top text-white">{{ title }}</div>
        <div class="p-2">Please <a :href="withPrefix('/login')">log in or register</a> to use this feature.</div>
    </Popper>
</template>
