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
            class="object-store-badge-popover">
            <p v-localize>{{ stockMessage }}</p>
            <div v-html="message"></div>
        </b-popover>
    </span>
</template>

<script>
import adminConfigMixin from "./adminConfigMixin";
import { FontAwesomeIcon, FontAwesomeLayers } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faUserLock,
    faChartLine,
    faBan,
    faCircleNotch,
    faPlug,
    faTachometerAlt,
    faArchive,
    faRecycle,
    faKey,
    faShieldAlt,
    faCloud,
} from "@fortawesome/free-solid-svg-icons";

library.add(
    faUserLock,
    faChartLine,
    faBan,
    faCircleNotch,
    faPlug,
    faTachometerAlt,
    faArchive,
    faRecycle,
    faKey,
    faShieldAlt,
    faCloud
);

const MESSAGES = {
    restricted:
        "This dataset is stored on storage restricted to a single user. It can not be shared, pubished, or added to Galaxy data libraries.",
    user_defined: "This storage was user defined and is not managed by the Galaxy adminstrator.",
    quota: "A Galaxy quota is enabled for this object store.",
    no_quota: "No Galaxy quota is enabled for this object store.",
    faster: "This storage has been marked as a faster option by the Galaxy adminstrator.",
    slower: "This storage has been marked as a slower option by the Galaxy adminstrator.",
    short_term: "This storage has been marked routinely purged by the Galaxy adminstrator.",
    backed_up: "This storage has been marked as backed up by the Galaxy adminstrator.",
    not_backed_up: "This storage has been marked as not backed up by the Galaxy adminstrator.",
    more_secure:
        "This storage has been marked as more secure by the Galaxy adminstrator. The Galaxy web application doesn't make any additional promises regarding security for this storage.",
    less_secure:
        "This storage has been marked as less secure by the Galaxy adminstrator. The Galaxy web application doesn't make any additional promises regarding security for this storage.",
    more_stable:
        "This storage has been marked as more stable by the Galaxy adminstrator - expect jobs to fail less because of storage issues for this storage.",
    less_stable:
        "This storage has been marked as less stable by the Galaxy adminstrator - expect jobs to fail more because of storage issues for this storage.",
    cloud: "This is cloud storage.",
};

export default {
    components: {
        FontAwesomeLayers,
        FontAwesomeIcon,
    },
    mixins: [adminConfigMixin],
    props: {
        badge: {
            type: Object,
            required: true,
        },
        size: {
            type: String,
            default: "3x",
        },
        moreOnHover: {
            type: Boolean,
            default: true,
        },
    },
    data() {
        return {
            advantage: "storage-advantage",
            disadvantage: "storage-disadvantage",
            neutral: "storage-neutral",
            transparent: "reduced-opacity",
        };
    },
    computed: {
        stockMessage() {
            return MESSAGES[this.badge.type];
        },
        layerClasses() {
            return [`fa-${this.size}`, "fa-fw"];
        },
        badgeType() {
            return this.badge.type;
        },
        shrink() {
            return { transform: "shrink-6" };
        },
        message() {
            return this.adminMarkup(this.badge.message);
        },
    },
};
</script>

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
