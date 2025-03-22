<script setup lang="ts">
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

interface Props {
    title: string;
}

const props = defineProps<Props>();

const breadcrumbItems = [{ title: "存储仪表盘", to: "StorageDashboard" }, { title: props.title }];
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <slot />
    </div>
</template>
