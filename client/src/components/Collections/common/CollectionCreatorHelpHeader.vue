<script setup lang="ts">
import { faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import localize from "@/utils/localization";

const isExpanded = ref(false);

function clickForHelp() {
    isExpanded.value = !isExpanded.value;
    return isExpanded.value;
}
</script>

<template>
    <div class="header flex-row no-flex">
        <div class="main-help well clear" :class="{ expanded: isExpanded }">
            <a
                class="more-help"
                href="javascript:void(0);"
                role="button"
                :title="localize('展开或关闭帮助')"
                @click="clickForHelp">
                <div v-if="!isExpanded">
                    <FontAwesomeIcon :icon="faChevronDown" />
                    <span class="sr-only">{{ localize("展开帮助") }}</span>
                </div>
                <div v-else>
                    <FontAwesomeIcon :icon="faChevronUp" />
                    <span class="sr-only">{{ localize("关闭帮助") }}</span>
                </div>
            </a>

            <div class="help-content">
                <!-- 每个扩展此组件的集合将添加他们自己的帮助内容 -->
                <slot></slot>

                <a
                    class="more-help"
                    href="javascript:void(0);"
                    role="button"
                    :title="localize('展开或关闭帮助')"
                    @click="clickForHelp">
                    <span class="sr-only">{{ localize("展开帮助") }}</span>
                </a>
            </div>
        </div>
    </div>
</template>

