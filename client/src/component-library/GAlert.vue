<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, useAttrs } from "vue";

const galaxyKwdToBoostrapDict: Record<string, string> = {
    done: "success",
    info: "info",
    warning: "warning",
    error: "danger",
};

defineProps({
    message: {
        type: String,
        default: "",
    },
});

const attrs = useAttrs();

const galaxyKwdToBootstrap = computed(() => {
    const variant: string = (attrs.status as string) || (attrs.variant as string);

    if (variant in galaxyKwdToBoostrapDict) {
        return galaxyKwdToBoostrapDict[variant];
    } else {
        return variant;
    }
});
</script>

<template>
    <BAlert v-bind="$attrs" :variant="galaxyKwdToBootstrap" v-on="$listeners">
        <slot> {{ message }} </slot>
    </BAlert>
</template>
