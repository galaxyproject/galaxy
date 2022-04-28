<template>
    <div>
        <div class="ui-portlet-section">
            <div class="portlet-header">
                <div class="portlet-operations">
                    <b-dropdown
                        v-b-tooltip.hover
                        no-caret
                        right
                        role="button"
                        title="Options"
                        variant="link"
                        aria-label="View all Options"
                        class="tool-dropdown float-right"
                        size="sm">
                        <template v-slot:button-content>
                            <span class="fa fa-caret-down" />
                        </template>
                        <b-dropdown-item @click="onCopyLink"
                            ><span class="fa fa-chain" /><span v-localize>Copy Link</span>
                        </b-dropdown-item>
                        <b-dropdown-item @click="onCopyId"
                            ><span class="fa fa-files-o" /><span v-localize>Copy Tool ID</span>
                        </b-dropdown-item>
                        <b-dropdown-item v-if="showDownload" @click="onDownload"
                            ><span class="fa fa-download" /><span v-localize>Download</span>
                        </b-dropdown-item>
                        <ToolSourceMenuItem :tool-id="id" />
                        <b-dropdown-item v-if="showLink" @click="onLink"
                            ><span class="fa fa-external-link" /><span v-localize
                                >See in Tool Shed</span
                            ></b-dropdown-item
                        >
                        <b-dropdown-item v-for="w of webhookDetails" :key="w.title" @click="w.onclick"
                            ><span :class="w.icon" />{{ w.title | l }}</b-dropdown-item
                        >
                    </b-dropdown>
                    <b-dropdown
                        v-if="showVersions"
                        v-b-tooltip.hover
                        no-caret
                        right
                        role="button"
                        title="Versions"
                        variant="link"
                        aria-label="Select Versions"
                        class="float-right tool-versions"
                        size="sm">
                        <template v-slot:button-content>
                            <span class="fa fa-cubes" />
                        </template>
                        <b-dropdown-item v-for="v of availableVersions" :key="v" @click="$emit('onChangeVersion', v)">
                            <span class="fa fa-cube" /><span v-localize>Switch to</span> {{ v }}</b-dropdown-item
                        >
                    </b-dropdown>
                    <b-button
                        v-if="showAddFavorite"
                        v-b-tooltip.hover
                        role="button"
                        title="Add to Favorites"
                        variant="link"
                        size="sm"
                        class="float-right"
                        @click="onAddFavorite">
                        <span class="fa fa-star-o" />
                    </b-button>
                    <b-button
                        v-else
                        v-b-tooltip.hover
                        role="button"
                        title="Remove from Favorites"
                        variant="link"
                        size="sm"
                        class="float-right"
                        @click="onRemoveFavorite">
                        <span class="fa fa-star" />
                    </b-button>
                </div>
                <div class="portlet-title">
                    <font-awesome-icon icon="wrench" class="portlet-title-icon fa-fw mr-1" />
                    <span class="portlet-title-text">
                        <b itemprop="name">{{ title }}</b> <span itemprop="description">{{ description }}</span> (Galaxy
                        Version {{ version }})
                    </span>
                </div>
            </div>

            <div class="portlet-content">
                <FormMessage :message="errorText" variant="danger" :persistent="true" />
                <FormMessage :message="messageText" :variant="messageVariant" />
                <slot name="body" />
                <div v-if="disabled" class="portlet-backdrop" />
            </div>
        </div>
        <slot name="buttons" />
        <div class="m-1">
            <ToolHelp :content="options.help" />
            <ToolFooter
                :id="options.id"
                :has-citations="options.citations"
                :xrefs="options.xrefs"
                :license="options.license"
                :creators="options.creator"
                :requirements="options.requirements" />
        </div>
    </div>
</template>
<script>
import ariaAlert from "utils/ariaAlert";
import { copyLink, copyId, downloadTool, openLink } from "./utilities";
import FormMessage from "components/Form/FormMessage";
import ToolFooter from "components/Tool/ToolFooter";
import ToolHelp from "components/Tool/ToolHelp";
import ToolSourceMenuItem from "components/Tool/ToolSourceMenuItem";
import Webhooks from "mvc/webhooks";
import { addFavorite, removeFavorite } from "components/Tool/services";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faWrench } from "@fortawesome/free-solid-svg-icons";

library.add(faWrench);

export default {
    components: {
        FontAwesomeIcon,
        FormMessage,
        ToolFooter,
        ToolHelp,
        ToolSourceMenuItem,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        user: {
            type: Object,
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
        options: {
            type: Object,
            required: true,
        },
        messageText: {
            type: String,
            required: true,
        },
        messageVariant: {
            type: String,
            default: "info",
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            webhookDetails: [],
            errorText: null,
        };
    },
    computed: {
        versions() {
            return this.options.versions;
        },
        showAddFavorite() {
            return !!this.user.email && !this.isFavorite;
        },
        showVersions() {
            return this.versions && this.versions.length > 1;
        },
        availableVersions() {
            const versions = this.versions.slice();
            const index = versions.indexOf(this.version);
            if (index > -1) {
                versions.splice(index, 1);
            }
            return versions.reverse();
        },
        showDownload() {
            return this.user && this.user.is_admin;
        },
        showLink() {
            return this.options.sharable_url;
        },
        isFavorite() {
            return this.getFavorites().tools.includes(this.id);
        },
    },
    watch: {
        id() {
            this.errorText = null;
        },
    },
    created() {
        // add tool menu webhooks
        Webhooks.load({
            type: "tool-menu",
            callback: (webhooks) => {
                webhooks.each((model) => {
                    const webhook = model.toJSON();
                    if (webhook.activate && webhook.config.function) {
                        this.webhookDetails.push({
                            icon: `fa ${webhook.config.icon}`,
                            title: webhook.config.title,
                            onclick: () => {
                                const func = new Function("options", webhook.config.function);
                                func(this.options);
                            },
                        });
                    }
                });
            },
        });
    },
    methods: {
        onAddFavorite() {
            addFavorite(this.user.id, this.id).then(
                (data) => {
                    this.errorText = null;
                    this.updateFavorites("tools", data);
                    ariaAlert("added to favorites");
                },
                () => {
                    this.errorText = `Failed to add '${this.id}' to favorites.`;
                    ariaAlert("failed to add to favorites");
                }
            );
        },
        onRemoveFavorite() {
            removeFavorite(this.user.id, this.id).then(
                (data) => {
                    this.errorText = null;
                    this.updateFavorites("tools", data);
                    ariaAlert("removed from favorites");
                },
                () => {
                    this.errorText = `Failed to remove '${this.id}' from favorites.`;
                    ariaAlert("failed to remove from favorites");
                }
            );
        },
        onCopyLink() {
            copyLink(this.id, "Link was copied to your clipboard");
        },
        onCopyId() {
            copyId(this.options.id, "Tool ID was copied to your clipboard");
        },
        onDownload() {
            downloadTool(this.id);
        },
        onLink() {
            openLink(this.options.sharable_url);
        },
        getFavorites() {
            const preferences = this.user.preferences;
            if (preferences && preferences.favorites) {
                return JSON.parse(preferences.favorites);
            } else {
                return {
                    tools: [],
                };
            }
        },
        updateFavorites(objectType, newFavorites) {
            const favorites = this.getFavorites();
            favorites[objectType] = newFavorites[objectType];
            this.$emit("onUpdateFavorites", this.user, JSON.stringify(favorites));
        },
    },
};
</script>
<style scoped>
.portlet-backdrop {
    display: block;
}
</style>
