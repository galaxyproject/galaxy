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
import { markup } from "@/components/ObjectStore/configurationMarkdown";

const MESSAGES = {
    restricted:
        "This dataset is stored on storage restricted to a single user. It can not be shared, published, or added to Galaxy data libraries.",
    user_defined: "This storage was user defined and is not managed by the Galaxy administrator.",
    quota: "A Galaxy quota is enabled for this storage location.",
    no_quota: "No Galaxy quota is enabled for this storage location.",
    faster: "This storage has been marked as a faster option by the Galaxy administrator.",
    slower: "This storage has been marked as a slower option by the Galaxy administrator.",
    short_term: "This storage has been marked as routinely purged by the Galaxy administrator.",
    backed_up: "This storage has been marked as backed up by the Galaxy administrator.",
    not_backed_up: "This storage has been marked as not backed up by the Galaxy administrator.",
    more_secure:
        "This storage has been marked as more secure by the Galaxy administrator. The Galaxy web application doesn't make any additional promises regarding security for this storage.",
    less_secure:
        "This storage has been marked as less secure by the Galaxy administrator. The Galaxy web application doesn't make any additional promises regarding security for this storage.",
    more_stable:
        "This storage has been marked as more stable by the Galaxy administrator - expect jobs to fail less because of storage issues for this storage.",
    less_stable:
        "This storage has been marked as less stable by the Galaxy administrator - expect jobs to fail more because of storage issues for this storage.",
    cloud: "This is cloud storage.",
};

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
    <span>
        <span ref="iconTarget" v-b-tooltip.hover.noninteractive="title" class="object-store-badge-wrapper">
            <FontAwesomeLayers :class="layerClasses" :data-badge-type="badgeType">
                <FontAwesomeIcon v-if="badgeType == 'restricted'" :icon="faUserLock" :class="disadvantage" />
                <FontAwesomeIcon v-if="badgeType == 'user_defined'" :icon="faPlug" :class="neutral" />
                <FontAwesomeIcon v-if="badgeType == 'quota'" :icon="faChartLine" :class="disadvantage" />
                <FontAwesomeIcon v-if="badgeType == 'no_quota'" :icon="faChartLine" :class="neutral" v-bind="shrink" />
                <FontAwesomeIcon v-if="badgeType == 'no_quota'" :icon="faBan" :class="[transparent, advantage]" />
                <FontAwesomeIcon v-if="badgeType == 'no_quota'" :icon="faCircleNotch" :class="advantage" />
                <FontAwesomeIcon
                    v-if="badgeType == 'no_quota'"
                    :icon="faCircleNotch"
                    :class="advantage"
                    flip="vertical" />
                <FontAwesomeIcon v-if="badgeType == 'faster'" :icon="faTachometerAlt" :class="advantage" />
                <FontAwesomeIcon
                    v-if="badgeType == 'slower'"
                    :icon="faTachometerAlt"
                    :class="disadvantage"
                    flip="horizontal" />
                <FontAwesomeIcon v-if="badgeType == 'short_term'" :icon="faRecycle" :class="disadvantage" />

                <FontAwesomeIcon v-if="badgeType == 'backed_up'" :icon="faArchive" :class="advantage" />
                <FontAwesomeIcon
                    v-if="badgeType == 'not_backed_up'"
                    :icon="faArchive"
                    :class="neutral"
                    v-bind="shrink" />
                <FontAwesomeIcon
                    v-if="badgeType == 'not_backed_up'"
                    :icon="faBan"
                    :class="[transparent, disadvantage]" />
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
                <FontAwesomeIcon
                    v-if="badgeType == 'less_stable'"
                    :icon="faShieldAlt"
                    :class="neutral"
                    v-bind="shrink" />
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
