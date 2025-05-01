<script setup lang="ts">
import ExternalLink from "@/components/ExternalLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

defineProps<{
    href?: string;
    title?: string;
    loading: boolean;
}>();
</script>

<template>
    <p>
        <LoadingSpan v-if="loading" message="正在加载实例配置" />
        <ExternalLink v-else-if="href" :href="href">
            {{ title ?? href }}
        </ExternalLink>
        <i v-else>配置值未设置，请联系Galaxy管理员。</i>
    </p>
</template>
