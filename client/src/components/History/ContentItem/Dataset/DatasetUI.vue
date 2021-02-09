<!--
The guts and markup of the dataset item separated from the
data assignment so we can re-use it on the collection listing

DO NOT put data retrieval into this component, access the dataset
either through the props, and make updates through the events -->

<template>
    <div
        class="dataset"
        :class="{ expanded, collapsed, selected }"
        :data-state="dataset.state"
        @keydown.arrow-left.self.stop="$emit('update:expanded', false)"
        @keydown.arrow-right.self.stop="$emit('update:expanded', true)"
        @keydown.space.self.stop.prevent="$emit('update:selected', !selected)"
    >
        <!-- name, state buttons, menus -->
        <nav
            class="content-top-menu d-flex align-items-center justify-content-between"
            @click.stop="$emit('update:expanded', !expanded)"
        >
            <div class="d-flex mr-1 align-items-center" @click.stop>
                <b-check v-if="showSelection" :checked="selected" @change="$emit('update:selected', $event)" />

                <StatusIcon v-if="!ok" class="status-icon px-1" :state="dataset.state" @click.stop="onStatusClick" />

                <StateBtn
                    v-if="!dataset.visible"
                    class="px-1"
                    state="hidden"
                    title="Unhide"
                    icon="fa fa-eye-slash"
                    @click.stop="$emit('unhide')"
                />
                <StateBtn
                    v-if="dataset.isDeleted && !dataset.purged"
                    class="px-1"
                    state="deleted"
                    title="Undelete"
                    icon="fas fa-trash-restore"
                    @click.stop="$emit('undelete')"
                />
            </div>

            <h5 class="flex-grow-1 overflow-hidden mr-auto text-nowrap text-truncate">
                <span class="hid">{{ dataset.hid }}</span>
                <span v-if="collapsed || !dataset.canEditName" class="name">{{ dataset.title }}</span>
            </h5>

            <slot name="menu">
                <DatasetMenu
                    class="content-item-menu"
                    :dataset="dataset"
                    :expanded="expanded"
                    v-on="$listeners"
                    :show-tags.sync="showTags"
                />
            </slot>
        </nav>

        <!--- read-only tags with name: prefix -->
        <div v-if="collapsed && dataset.nameTags.length" class="nametags p-1">
            <Nametag v-for="tag in dataset.nameTags" :key="tag" :tag="tag" />
        </div>

        <!-- expanded view with editors -->
        <header v-if="expanded" class="p-2">
            <ClickToEdit
                v-if="dataset.canEditName"
                tag-name="h4"
                :value="dataset.name"
                @input="$emit('update:dataset', { name: $event })"
                :display-label="dataset.title"
                :tooltip-title="'Edit dataset name...' | localize"
                tooltip-placement="left"
            />

            <Annotation
                class="mt-1"
                :value="dataset.annotation"
                @input="$emit('update:dataset', { annotation: $event })"
            />

            <ContentTags v-if="showTags" class="mt-2" :content="dataset" />
            <div v-else-if="dataset.nameTags.length" class="nametags mt-2">
                <Nametag v-for="tag in dataset.nameTags" :key="tag" :tag="tag" />
            </div>

            <div class="details">
                <DatasetSummary :dataset="dataset" />

                <div class="display-applications" v-if="dataset.displayLinks.length">
                    <div class="display-application" v-for="app in dataset.displayLinks" :key="app.label">
                        <span class="display-application-location">
                            {{ app.label }}
                        </span>
                        <span class="display-application-links">
                            <a v-for="l in app.links" :key="l.href" :href="l.href" :target="l.target">
                                {{ l.text }}
                            </a>
                        </span>
                    </div>
                </div>
                <pre v-if="dataset.peek" class="dataset-peek p-1" v-html="dataset.peek"></pre>
            </div>
        </header>
    </div>
</template>

<script>
import { Dataset, STATES } from "../../model";
import ClickToEdit from "components/ClickToEdit";
import Annotation from "components/Annotation";
import { Nametag } from "components/Nametags";
import { StatusIcon, StateBtn } from "../../StatusIcon";
import DatasetMenu from "./DatasetMenu";
import DatasetSummary from "./Summary";
import ContentTags from "../../ContentTags";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        ClickToEdit,
        Annotation,
        StatusIcon,
        StateBtn,
        DatasetMenu,
        DatasetSummary,
        ContentTags,
        Nametag,
    },
    props: {
        dataset: { type: Dataset, required: true },
        expanded: { type: Boolean, required: true },
        selected: { type: Boolean, required: false, default: false },
        showSelection: { type: Boolean, required: false, default: false },
    },
    data() {
        return {
            showTags: false,
        };
    },
    computed: {
        collapsed() {
            return !this.expanded;
        },
        typeId() {
            return this.dataset.type_id;
        },
        ok() {
            return this.dataset.state == "ok";
        },
    },
    methods: {
        onStatusClick(evt) {
            switch (this.dataset.state) {
                case STATES.ERROR:
                    this.backboneRoute("datasets/error", { dataset_id: this.dataset.id });
                    break;
                default:
                    console.log("unhandled status icon click", this.dataset.state);
            }
        },
    },
};
</script>
