<script setup lang="ts">
import { reactive } from "vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

import DiskUsageSummary from "./DiskUsageSummary.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import Heading from "@/components/Common/Heading.vue";
import IconCard from "@/components/IconCard.vue";

const router = useRouter();

const texts = reactive({
    title: localize("存储仪表板"),
    subtitle: localize("在这里您可以查看您的磁盘使用状态概览。"),
    freeSpace: {
        title: localize("您的使用空间超出预期了吗？"),
        description: localize(
            "找出是什么占用了您的空间，了解如何轻松安全地释放一些空间。"
        ),
        icon: "fas fa-broom fa-6x",
        buttonText: localize("释放磁盘空间"),
    },
    explore_by_history: {
        title: localize("按历史记录可视化探索您的磁盘使用情况"),
        description: localize(
            "想知道哪些历史记录或数据集在您的账户中占用最多空间？在这里，您可以按历史记录以可视化方式探索您的磁盘使用情况。"
        ),
        icon: "fas fa-chart-pie fa-6x",
        buttonText: localize("立即探索"),
    },
    explore_by_objectstore: {
        title: localize("按存储位置可视化探索您的磁盘使用情况"),
        description: localize(
            "想知道您账户中的空间是如何分布在各个存储位置的吗？在这里，您可以按照数据物理存储的位置以可视化方式探索您的磁盘使用情况。"
        ),
        icon: "fas fa-hdd fa-6x",
        buttonText: localize("立即探索"),
    },
});

const breadcrumbItems = [{ title: texts.title }];

function goToStorageManager() {
    router.push({ name: "StorageManager" });
}

function goToHistoriesOverview() {
    router.push({ name: "HistoriesOverview" });
}

function goToObjectStoresOverview() {
    router.push({ name: "ObjectStoresOverview" });
}
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <Heading h2 size="sm">
            {{ texts.subtitle }}
        </Heading>

        <DiskUsageSummary class="m-3" />

        <IconCard
            class="mx-auto mb-3"
            data-description="释放空间卡片"
            :title="texts.freeSpace.title"
            :description="texts.freeSpace.description"
            :icon="texts.freeSpace.icon"
            :button-text="texts.freeSpace.buttonText"
            @onButtonClick="goToStorageManager" />

        <IconCard
            class="mx-auto mb-3"
            data-description="探索使用情况卡片"
            :title="texts.explore_by_history.title"
            :description="texts.explore_by_history.description"
            :icon="texts.explore_by_history.icon"
            :button-text="texts.explore_by_history.buttonText"
            @onButtonClick="goToHistoriesOverview" />

        <IconCard
            class="mx-auto mb-3"
            data-description="探索对象存储使用情况卡片"
            :title="texts.explore_by_objectstore.title"
            :description="texts.explore_by_objectstore.description"
            :icon="texts.explore_by_objectstore.icon"
            :button-text="texts.explore_by_objectstore.buttonText"
            @onButtonClick="goToObjectStoresOverview" />
    </div>
</template>
