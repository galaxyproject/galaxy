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
                :title="localize('Expand or Close Help')"
                @click="clickForHelp">
                <div v-if="!isExpanded">
                    <FontAwesomeIcon :icon="faChevronDown" />
                    <span class="sr-only">{{ localize("Expand Help") }}</span>
                </div>
                <div v-else>
                    <FontAwesomeIcon :icon="faChevronUp" />
                    <span class="sr-only">{{ localize("Close Help") }}</span>
                </div>
            </a>

            <div class="help-content">
                <!-- each collection that extends this will add their own help content -->
                <slot></slot>

                <a
                    class="more-help"
                    href="javascript:void(0);"
                    role="button"
                    :title="localize('Expand or Close Help')"
                    @click="clickForHelp">
                    <span class="sr-only">{{ localize("Expand Help") }}</span>
                </a>
            </div>
        </div>
    </div>
</template>
