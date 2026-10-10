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
import { computed, ref } from "vue";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";
import { MESSAGES } from "@/components/ObjectStore/badgeMessages";

import GPopover from "@/components/BaseComponents/GPopover.vue";
import ConfigurationMarkdown from "@/components/ObjectStore/ConfigurationMarkdown.vue";

interface Props {
    badge: ObjectStoreBadgeType;
    size?: string;
    /** Focusable trigger whose popover links can be reached; turn off inside dropdown options */
    interactive?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    size: "lg",
    interactive: true,
});

const trigger = ref<HTMLElement>();

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
</script>

<template>
    <component
        :is="interactive ? 'button' : 'span'"
        ref="trigger"
        :type="interactive ? 'button' : undefined"
        :role="interactive ? undefined : 'img'"
        :aria-label="stockMessage"
        class="object-store-badge-wrapper">
        <FontAwesomeLayers :class="layerClasses" :data-badge-type="badgeType">
            <FontAwesomeIcon v-if="badgeType == 'restricted'" :icon="faUserLock" :class="disadvantage" />
            <FontAwesomeIcon v-if="badgeType == 'user_defined'" :icon="faPlug" :class="neutral" />
            <FontAwesomeIcon v-if="badgeType == 'quota'" :icon="faChartLine" :class="disadvantage" />
            <FontAwesomeIcon v-if="badgeType == 'no_quota'" v-bind="shrink" :icon="faChartLine" :class="neutral" />
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
            <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" v-bind="shrink" :icon="faArchive" :class="neutral" />
            <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" :icon="faBan" :class="[transparent, disadvantage]" />
            <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" :icon="faCircleNotch" :class="disadvantage" />
            <FontAwesomeIcon
                v-if="badgeType == 'not_backed_up'"
                :icon="faCircleNotch"
                :class="disadvantage"
                flip="vertical" />

            <FontAwesomeIcon v-if="badgeType == 'more_secure'" :icon="faKey" :class="advantage" />
            <FontAwesomeIcon v-if="badgeType == 'less_secure'" v-bind="shrink" :icon="faKey" :class="neutral" />
            <FontAwesomeIcon v-if="badgeType == 'less_secure'" :icon="faBan" :class="[transparent, disadvantage]" />
            <FontAwesomeIcon v-if="badgeType == 'less_secure'" :icon="faCircleNotch" :class="disadvantage" />
            <FontAwesomeIcon
                v-if="badgeType == 'less_secure'"
                :icon="faCircleNotch"
                :class="disadvantage"
                flip="vertical" />

            <FontAwesomeIcon v-if="badgeType == 'more_stable'" :icon="faShieldAlt" :class="advantage" />
            <FontAwesomeIcon v-if="badgeType == 'less_stable'" v-bind="shrink" :icon="faShieldAlt" :class="neutral" />
            <FontAwesomeIcon v-if="badgeType == 'less_stable'" :icon="faBan" :class="[transparent, disadvantage]" />
            <FontAwesomeIcon v-if="badgeType == 'less_stable'" :icon="faCircleNotch" :class="disadvantage" />
            <FontAwesomeIcon
                v-if="badgeType == 'less_stable'"
                :icon="faCircleNotch"
                :class="disadvantage"
                flip="vertical" />

            <FontAwesomeIcon v-if="badgeType == 'cloud'" :icon="faCloud" :class="neutral" />
        </FontAwesomeLayers>
    </component>
    <GPopover
        :target="() => trigger"
        :interactive="interactive && !!message"
        :aria-label="stockMessage"
        triggers="hover"
        placement="top">
        <p>{{ stockMessage }}</p>
        <ConfigurationMarkdown v-if="message" :markdown="message" :admin="true" />
    </GPopover>
</template>

<style scoped>
button.object-store-badge-wrapper {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    line-height: inherit;
    cursor: default;
}

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
