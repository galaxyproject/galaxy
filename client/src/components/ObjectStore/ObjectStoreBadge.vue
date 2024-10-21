<script setup lang="ts">
import "./badgeIcons";

import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import { type components } from "@/api/schema";

import ConfigurationMarkdown from "./ConfigurationMarkdown.vue";

type BadgeType = components["schemas"]["BadgeDict"];

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

interface ObjectStoreBadgeProps {
    badge: BadgeType;
    size?: string;
    moreOnHover?: boolean;
}

const props = withDefaults(defineProps<ObjectStoreBadgeProps>(), {
    size: "3x",
    moreOnHover: true,
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
</script>

<template>
    <span>
        <span ref="iconTarget" class="object-store-badge-wrapper">
            <FontAwesomeLayers :class="layerClasses" :data-badge-type="badgeType">
                <FontAwesomeIcon v-if="badgeType == 'restricted'" icon="user-lock" :class="disadvantage" />
                <FontAwesomeIcon v-if="badgeType == 'user_defined'" icon="plug" :class="neutral" />
                <FontAwesomeIcon v-if="badgeType == 'quota'" icon="chart-line" :class="disadvantage" />
                <FontAwesomeIcon v-if="badgeType == 'no_quota'" icon="chart-line" :class="neutral" v-bind="shrink" />
                <FontAwesomeIcon v-if="badgeType == 'no_quota'" icon="ban" :class="[transparent, advantage]" />
                <FontAwesomeIcon v-if="badgeType == 'no_quota'" icon="circle-notch" :class="advantage" />
                <FontAwesomeIcon
                    v-if="badgeType == 'no_quota'"
                    icon="circle-notch"
                    :class="advantage"
                    flip="vertical" />
                <FontAwesomeIcon v-if="badgeType == 'faster'" icon="tachometer-alt" :class="advantage" />
                <FontAwesomeIcon
                    v-if="badgeType == 'slower'"
                    icon="tachometer-alt"
                    :class="disadvantage"
                    flip="horizontal" />
                <FontAwesomeIcon v-if="badgeType == 'short_term'" icon="recycle" :class="disadvantage" />

                <FontAwesomeIcon v-if="badgeType == 'backed_up'" icon="archive" :class="advantage" />
                <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" icon="archive" :class="neutral" v-bind="shrink" />
                <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" icon="ban" :class="[transparent, disadvantage]" />
                <FontAwesomeIcon v-if="badgeType == 'not_backed_up'" icon="circle-notch" :class="disadvantage" />
                <FontAwesomeIcon
                    v-if="badgeType == 'not_backed_up'"
                    icon="circle-notch"
                    :class="disadvantage"
                    flip="vertical" />

                <FontAwesomeIcon v-if="badgeType == 'more_secure'" icon="key" :class="advantage" />
                <FontAwesomeIcon v-if="badgeType == 'less_secure'" icon="key" :class="neutral" v-bind="shrink" />
                <FontAwesomeIcon v-if="badgeType == 'less_secure'" icon="ban" :class="[transparent, disadvantage]" />
                <FontAwesomeIcon v-if="badgeType == 'less_secure'" icon="circle-notch" :class="disadvantage" />
                <FontAwesomeIcon
                    v-if="badgeType == 'less_secure'"
                    icon="circle-notch"
                    :class="disadvantage"
                    flip="vertical" />

                <FontAwesomeIcon v-if="badgeType == 'more_stable'" icon="shield-alt" :class="advantage" />
                <FontAwesomeIcon v-if="badgeType == 'less_stable'" icon="shield-alt" :class="neutral" v-bind="shrink" />
                <FontAwesomeIcon v-if="badgeType == 'less_stable'" icon="ban" :class="[transparent, disadvantage]" />
                <FontAwesomeIcon v-if="badgeType == 'less_stable'" icon="circle-notch" :class="disadvantage" />
                <FontAwesomeIcon
                    v-if="badgeType == 'less_stable'"
                    icon="circle-notch"
                    :class="disadvantage"
                    flip="vertical" />

                <FontAwesomeIcon v-if="badgeType == 'cloud'" icon="cloud" :class="neutral" />
            </FontAwesomeLayers>
        </span>
        <b-popover
            v-if="moreOnHover"
            :target="
                () => {
                    return $refs.iconTarget;
                }
            "
            triggers="hover"
            placement="bottom"
            variant="secondary"
            class="object-store-badge-popover">
            <p v-localize>{{ stockMessage }}</p>
            <ConfigurationMarkdown v-if="message" :markdown="message" :admin="true" />
        </b-popover>
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
