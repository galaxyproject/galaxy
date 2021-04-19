<template>
    <div>
        <div class="ui-portlet-section">
            <div class="portlet-header">
                <div class="portlet-operations">
                    <b-dropdown
                        no-caret
                        right
                        role="button"
                        title="Options"
                        variant="link"
                        aria-label="View all Options"
                        class="float-right py-0 px-1"
                        button-class="p-0"
                        size="sm"
                        v-b-tooltip.hover
                    >
                        <template v-slot:button-content>
                            <span class="fa fa-caret-down" />
                        </template>
                        <b-dropdown-item @click="onCopyLink"> <span class="fa fa-chain" /> Copy Link </b-dropdown-item>
                        <b-dropdown-item @click="onCopyId">
                            <span class="fa fa-files-o" /> Copy Tool ID
                        </b-dropdown-item>
                        <b-dropdown-item v-if="showDownload" @click="onDownload">
                            <span class="fa fa-download" /> Download
                        </b-dropdown-item>
                        <b-dropdown-item v-if="showLink" @click="onLink">
                            <span class="fa fa-external-link" /> See in Tool Shed
                        </b-dropdown-item>
                        <b-dropdown-item v-for="w of webhookDetails" :key="w.title" @click="w.onclick">
                            <span :class="w.icon" /> {{ w.title }}
                        </b-dropdown-item>
                    </b-dropdown>
                    <b-dropdown
                        v-if="showVersions"
                        no-caret
                        right
                        role="button"
                        title="Versions"
                        variant="link"
                        aria-label="Select Versions"
                        class="float-right py-0 px-1"
                        button-class="p-0"
                        size="sm"
                        v-b-tooltip.hover
                    >
                        <template v-slot:button-content>
                            <span class="fa fa-cubes" />
                        </template>
                        <b-dropdown-item v-for="v of reversedVersions" :key="v" @click="$emit('onChangeVersion', v)">
                            <span class="fa fa-cube" /> Switch to {{ v }}
                        </b-dropdown-item>
                    </b-dropdown>
                    <b-button
                        v-if="showAddFavorite"
                        role="button"
                        title="Add to Favorites"
                        variant="link"
                        size="sm"
                        class="float-right py-0 px-1"
                        v-b-tooltip.hover
                        @click="onAddFavorite"
                    >
                        <span class="fa fa-star-o" />
                    </b-button>
                    <b-button
                        v-else
                        role="button"
                        title="Remove from Favorites"
                        variant="link"
                        size="sm"
                        class="float-right py-0 px-1"
                        v-b-tooltip.hover
                        @click="onRemoveFavorite"
                    >
                        <span class="fa fa-star" />
                    </b-button>
                </div>
                <div class="portlet-title">
                    <i class="portlet-title-icon fa mr-1 fa-wrench" style="display: inline"></i>
                    <span class="portlet-title-text">
                        <b itemprop="name">{{ title }}</b> <span itemprop="description">{{ description }}</span> (Galaxy
                        Verson {{ version }})
                    </span>
                </div>
            </div>
            <div class="portlet-content">
                <slot name="body" />
            </div>
        </div>
        <div class="m-1">
            <ToolHelp :content="options.help" />
            <ToolFooter
                :id="options.id"
                :hasCitations="options.citations"
                :xrefs="options.xrefs"
                :license="options.license"
                :creators="options.creator"
                :requirements="options.requirements"
            />
        </div>
    </div>
</template>
<script>
import axios from "axios";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import ariaAlert from "utils/ariaAlert";
import { copy } from "utils/clipboard";
import ToolFooter from "components/Tool/ToolFooter";
import ToolHelp from "components/Tool/ToolHelp";
import Webhooks from "mvc/webhooks";

export default {
    components: {
        ToolFooter,
        ToolHelp,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        version: {
            type: String,
            required: false,
        },
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            required: false,
        },
        sustainVersion: {
            type: Boolean,
            default: false,
        },
        options: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            isFavorite: this.getFavorite(),
            webhookDetails: [],
        };
    },
    computed: {
        versions() {
            return this.options.versions;
        },
        showAddFavorite() {
            return !this.getUser().isAnonymous() && !this.isFavorite;
        },
        showVersions() {
            return !this.sustainVersion && this.versions && this.versions.length > 1;
        },
        reversedVersions() {
            return this.versions.reverse();
        },
        showDownload() {
            const user = this.getUser();
            return user && user.get("is_admin");
        },
        showLink() {
            return this.options.sharable_url;
        },
    },
    created() {
        // add tool menu webhooks
        Webhooks.load({
            type: "tool-menu",
            callback: function (webhooks) {
                webhooks.each((model) => {
                    const webhook = model.toJSON();
                    if (webhook.activate && webhook.config.function) {
                        this.webhookDetails.push({
                            icon: `fa ${webhook.config.icon}`,
                            title: webhook.config.title,
                            onclick: function () {
                                const func = new Function("options", webhook.config.function);
                                func(options);
                            },
                        });
                    }
                });
            },
        });
    },
    methods: {
        getUser() {
            const galaxy = getGalaxyInstance();
            return galaxy.user;
        },
        getFavorite() {
            return this.getUser().getFavorites().tools.indexOf(this.id) >= 0;
        },
        onAddFavorite() {
            const user = this.getUser();
            axios
                .put(`${getAppRoot()}api/users/${user.id}/favorites/tools`, { object_id: this.id })
                .then((response) => {
                    user.updateFavorites("tools", response.data);
                    this.isFavorite = this.getFavorite();
                    ariaAlert("added to favorites");
                });
        },
        onRemoveFavorite() {
            const user = this.getUser();
            axios
                .delete(`${getAppRoot()}api/users/${user.id}/favorites/tools/${encodeURIComponent(this.id)}`)
                .then((response) => {
                    user.updateFavorites("tools", response.data);
                    this.isFavorite = this.getFavorite();
                    ariaAlert("removed from favorites");
                });
        },
        onCopyLink() {
            copy(
                `${window.location.origin + getAppRoot()}root?tool_id=${this.id}`,
                "Link was copied to your clipboard"
            );
        },
        onCopyId() {
            copy(`${options.id}`, "Tool ID was copied to your clipboard");
        },
        onDownload() {
            window.location.href = `${getAppRoot()}api/tools/${this.id}/download`;
        },
        onLink() {
            window.open(this.options.sharable_url);
        },
    },
};
</script>
