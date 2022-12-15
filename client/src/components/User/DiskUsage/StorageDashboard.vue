<script setup lang="ts">
import _l from "@/utils/localization";
import DiskUsageSummary from "./DiskUsageSummary.vue";
import IconCard from "@/components/IconCard.vue";
import { reactive } from "vue";
import { useRouter } from "vue-router/composables";

const router = useRouter();

const texts = reactive({
    title: _l("Storage Dashboard"),
    subtitle: _l("Here you can see an overview of your disk usage status."),
    freeSpace: {
        title: _l("Is your usage more than expected?"),
        description: _l("Find out what is eating up your space and learn how to easily and safely free up some of it."),
        icon: "fas fa-broom fa-6x",
        buttonText: _l("Free up disk usage"),
    },
});

function goToStorageManager() {
    router.push({ name: "StorageManager" });
}
</script>

<template>
    <div>
        <header class="main-header">
            <h1 class="text-center my-3">
                <b>{{ texts.title }}</b>
            </h1>
            <h2 class="text-center my-3 h-sm">{{ texts.subtitle }}</h2>
        </header>
        <disk-usage-summary class="m-3" />
        <icon-card
            class="mx-auto"
            :title="texts.freeSpace.title"
            :description="texts.freeSpace.description"
            :icon="texts.freeSpace.icon"
            :button-text="texts.freeSpace.buttonText"
            @onButtonClick="goToStorageManager" />
    </div>
</template>
