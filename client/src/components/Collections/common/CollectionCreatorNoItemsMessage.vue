<script setup lang="ts">
import { BAlert, BLink } from "bootstrap-vue";

import localize from "@/utils/localization";

const emit = defineEmits<{
    (e: "click-upload"): void;
}>();
</script>
<template>
    <BAlert variant="info" show>
        {{ localize("没有可用项来创建集合。") }}
        {{ localize("退出并更改当前历史记录，或者") }}
        <BLink class="text-decoration-none" @click.stop.prevent="emit('click-upload')">
            {{ localize("上传一些数据集。") }}
        </BLink>
    </BAlert>
</template>