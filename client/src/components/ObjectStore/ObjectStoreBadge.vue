<script setup lang="ts">
import {
    faArchive,
    faBan,
    faChartLine,
    faCircleNotch,
    faCloud,
    faKey,
    faPlug,
    faRecycle,
    faShieldAlt,
    faTachometerAlt,
    faUserLock,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";
import { MESSAGES } from "@/components/ObjectStore/badgeMessages";
import { markup } from "@/components/ObjectStore/configurationMarkdown";

interface Props {
    badge: ObjectStoreBadgeType;
    size?: string;
}

const props = withDefaults(defineProps<Props>(), {
    size: "lg",
});

const advantage = "storage-advantage";
const disadvantage = "storage-disadvantage";
const neutral = "storage-neutral";
const transparent = "reduced-opacity";

const stockMessage = computed(() => {
    return MESSAGES[props.badge.type];
});

const layerClasses = computed(() => {
    return [`fa-${props.size}`, "fa-fw"];
});

const badgeType = computed(() => {
    return props.badge.type;
});

const shrink = computed(() => {
    return { transform: "shrink-6" };
});

const message = computed<string>(() => {
    return props.badge.message || "";
});

const title = computed(() => {
    return stockMessage.value + (message.value ? "\n\n" + markup(message.value ?? "", true) : "");
});
</script>

<template>
    <span v-b-tooltip.hover.noninteractive="title" class="object-store-badge-wrapper">
        <FontAwesomeLayers :class="layerClasses" :data-badge-type="badgeType">
            <FontAwesomeIcon v-if="badgeType == 'restricted'" :icon="faUserLock" :class="disadvantage" />
            <FontAwesomeIcon v-if="badgeType == 'user_defined'" :icon="faPlug" :class="neutral" />
            <FontAwesomeIcon v-if="badgeType == 'quota'" :icon="faChartLine" :class="disadvantage" />
            <FontAwesomeIcon v-if="badgeType == 'no_quota'" :icon="faChartLine" :class="neutral" v-bind="shrink" />
            <FontAwesomeIcon v-if="badgeType == 'no_quota'" :icon="faBan" :class="[transparent, advantage]" />
            <FontAwesomeIcon v-if="badgeType == 'no_quota'" :icon="faCircleNotch" :class="advantage" />
            <FontAwesomeIcon v-if="badgeType == 'no_quota'" :icon="faCircleNotch" :class="advantage" flip="vertical" />
            <FontAwesomeIcon v-if="badgeType == 'faster'" :icon="faTachometerAlt" :class="advantage" />
            <FontAwesomeIcon
                v-if="badgeType == 'slower'"
                :icon="faTachometerAlt"
                :class="disadvantage"
                flip="horizontal" />
            <FontAwesomeIcon v-if="badgeType == 'short_term'" :icon="faRecycle" :class="disadvantage" />

            <FontAwesomeIcon v-if="badgeType == 'backed_up'" :icon="faArchive" :class="advantage" />
            <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" :icon="faArchive" :class="neutral" v-bind="shrink" />
            <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" :icon="faBan" :class="[transparent, disadvantage]" />
            <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" :icon="faCircleNotch" :class="disadvantage" />
            <FontAwesomeIcon
                v-if="badgeType == 'not_backed_up'"
                :icon="faCircleNotch"
                :class="disadvantage"
                flip="vertical" />

            <FontAwesomeIcon v-if="badgeType == 'more_secure'" :icon="faKey" :class="advantage" />
            <FontAwesomeIcon v-if="badgeType == 'less_secure'" :icon="faKey" :class="neutral" v-bind="shrink" />
            <FontAwesomeIcon v-if="badgeType == 'less_secure'" :icon="faBan" :class="[transparent, disadvantage]" />
            <FontAwesomeIcon v-if="badgeType == 'less_secure'" :icon="faCircleNotch" :class="disadvantage" />
            <FontAwesomeIcon
                v-if="badgeType == 'less_secure'"
                :icon="faCircleNotch"
                :class="disadvantage"
                flip="vertical" />

            <FontAwesomeIcon v-if="badgeType == 'more_stable'" :icon="faShieldAlt" :class="advantage" />
            <FontAwesomeIcon v-if="badgeType == 'less_stable'" :icon="faShieldAlt" :class="neutral" v-bind="shrink" />
            <FontAwesomeIcon v-if="badgeType == 'less_stable'" :icon="faBan" :class="[transparent, disadvantage]" />
            <FontAwesomeIcon v-if="badgeType == 'less_stable'" :icon="faCircleNotch" :class="disadvantage" />
            <FontAwesomeIcon
                v-if="badgeType == 'less_stable'"
                :icon="faCircleNotch"
                :class="disadvantage"
                flip="vertical" />

            <FontAwesomeIcon v-if="badgeType == 'cloud'" :icon="faCloud" :class="neutral" />
        </FontAwesomeLayers>
    </span>
</template>

<style scoped>
.reduced-opacity {
    opacity: 0.65;
}

.storage-advantage {
    color: #94db94;
}

.storage-neutral {
    color: #2a3f59;
}

.storage-disadvantage {
    color: #fea54e;
}
</style>
