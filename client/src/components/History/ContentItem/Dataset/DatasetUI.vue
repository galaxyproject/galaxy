<!--
The guts and markup of the dataset item separated from the
data assignment so we can re-use it on the collection listing

DO NOT put data retrieval into this component, access the dataset
either through the props, and make updates through the events -->

<template>
    <div
        class="dataset history-content"
        :id="typeId"
        :class="{ expanded, collapsed, selected }"
        :data-hid="dataset.hid"
        :data-state="dataset.state"
        @keydown.arrow-left.self.stop="$emit('update:expanded', false)"
        @keydown.arrow-right.self.stop="$emit('update:expanded', true)"
        @keydown.space.self.stop.prevent="$emit('update:selected', !selected)">
        <!-- name, state buttons, menus -->
        <nav class="content-top-menu p-1 d-flex cursor-pointer" @click.stop="$emit('update:expanded', !expanded)">
            <div class="d-flex flex-grow-1 overflow-hidden">
                <div class="pl-1" v-if="showSelectionBox">
                    <b-check class="selector" :checked="selected" @change="$emit('update:selected', $event)"></b-check>
                </div>

                <StatusIcon
                    v-if="!collapsed"
                    class="status-icon px-1"
                    :state="dataset.state"
                    @click.stop="onStatusClick" />

                <IconButton
                    v-if="!collapsed && !dataset.visible"
                    class="px-1"
                    state="hidden"
                    title="Unhide"
                    icon="eye-slash"
                    @click.stop="$emit('unhide')" />

                <IconButton
                    v-if="!collapsed && dataset.isDeleted && !dataset.purged"
                    class="px-1"
                    state="deleted"
                    title="Undelete"
                    icon="trash-restore"
                    @click.stop="$emit('undelete')" />

                <div class="content-title title p-1 overflow-hidden">
                    <h5 class="text-truncate" v-if="collapsed">
                        <span class="hid" data-description="dataset hid">{{ dataset.hid }}</span>
                        <span class="name" data-description="dataset name">{{ dataset.title }}</span>
                    </h5>
                </div>
            </div>

            <div class="d-flex">
                <slot name="menu">
                    <DatasetMenu
                        :dataset="dataset"
                        :expanded="expanded"
                        :writable="writable"
                        @edit="edit"
                        v-on="$listeners" />
                </slot>
            </div>
        </nav>

        <!--- read-only tags with name: prefix -->
        <div v-if="collapsed && dataset.nameTags.length" class="nametags px-2 pb-2">
            <Nametag v-for="tag in dataset.nameTags" :key="tag" :tag="tag" />
        </div>

        <div v-if="expanded" class="p-3 details">
            <div class="d-flex">
                <div class="flex-grow-1">
                    <h4 data-description="dataset name">{{ name || "(Dataset Name)" }}</h4>

                    <template v-if="!editing">
                        <p v-if="annotation">{{ annotation }}</p>
                        <div v-if="dataset.nameTags.length" class="nametags mt-2">
                            <Nametag v-for="tag in dataset.nameTags" :key="tag" :tag="tag" />
                        </div>
                    </template>

                    <div v-else class="my-3">
                        <b-textarea
                            class="mb-3"
                            v-model="name"
                            placeholder="Dataset Name"
                            trim
                            max-rows="4"></b-textarea>

                        <b-textarea
                            class="mb-3"
                            v-model="annotation"
                            placeholder="Annotation (optional)"
                            trim
                            max-rows="4"></b-textarea>

                        <StatelessTags class="mt-2" v-model="tags" />
                    </div>
                </div>

                <EditorMenu
                    class="ml-3 flex-grow-0 d-flex flex-column"
                    v-if="writable"
                    model-name="Dataset"
                    :editing.sync="editing"
                    :writable="writable"
                    :valid="valid"
                    :dirty="dirty"
                    @save="save"
                    @revert="revert" />
            </div>

            <div class="details">
                

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
        </div>
    </div>
</template>

<script>
import { Dataset, STATES } from "components/History/model";
import { Nametag } from "components/Nametags";
import StatusIcon from "components/History/StatusIcon";
import DatasetMenu from "./DatasetMenu";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import IconButton from "components/IconButton";
import EditorMenu from "components/History/EditorMenu";
import { StatelessTags } from "components/Tags";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        StatusIcon,
        DatasetMenu,
        Nametag,
        IconButton,
        EditorMenu,
        StatelessTags,
    },
    props: {
        dataset: { type: Dataset, required: true },
        expanded: { type: Boolean, required: true },
        selected: { type: Boolean, required: false, default: false },
        showSelection: { type: Boolean, required: false, default: false },
        writable: { type: Boolean, required: false, default: true },
        selectable: { type: Boolean, required: false, default: true },
    },
    data() {
        return {
            editing: false,
            tempContent: this.dataset.clone(),
        };
    },
    computed: {
        collapsed() {
            return !this.expanded;
        },
        typeId() {
            return this.dataset.type_id;
        },
        isEditing() {
            return this.writable && this.editing;
        },
        valid() {
            return true;
        },
        dirty() {
            return !this.tempContent.equals(this.dataset);
        },
        name: {
            get() {
                return this.tempContent?.name || "";
            },
            set(newVal) {
                this.patchTempContent({ name: newVal });
            },
        },
        annotation: {
            get() {
                return this.tempContent?.annotation || "";
            },
            set(newVal) {
                this.patchTempContent({ annotation: newVal });
            },
        },
        tags: {
            get() {
                return this.tempContent?.tags || [];
            },
            set(newTags) {
                if (Array.isArray(newTags)) {
                    this.patchTempContent({ tags: newTags });
                }
            },
        },
        showSelectionBox() {
            return this.selectable && this.showSelection;
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
        patchTempContent(props = {}) {
            this.tempContent = this.tempContent.patch(props);
        },
        save() {
            if (this.valid) {
                this.$emit("update:dataset", this.tempContent);
                this.editing = false;
            }
        },
        reset() {
            this.tempContent = this.dataset.clone();
        },
        revert() {
            if (this.dirty) {
                this.reset();
            }
        },
        edit() {
            this.backboneRoute("datasets/edit", { dataset_id: this.dataset.id });
        },
    },
};
</script>
