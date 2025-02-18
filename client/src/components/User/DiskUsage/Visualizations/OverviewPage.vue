<script setup lang="ts">
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";

interface Props {
    title: string;
}

const props = defineProps<Props>();

const breadcrumbItems = [
    { title: "User Preferences", to: "/user" },
    { title: "Storage Dashboard", to: "StorageDashboard" },
    { title: props.title },
];
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <slot />
    </div>
</template>
