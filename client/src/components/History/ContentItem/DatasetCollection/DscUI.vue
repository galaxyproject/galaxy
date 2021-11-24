<!-- UI only, updates/changes to data should be handled outside
    this component via events emissions -->

<template>
    <div
        class="dataset dataset-collection collapsed"
        :class="{ selected }"
        :id="typedId"
        :data-state="dsc.state"
        @keydown.arrow-right.self.stop="$emit('viewCollection')"
        @keydown.space.self.stop.prevent="$emit('update:selected', !selected)">
        <nav class="content-top-menu p-1 d-flex cursor-pointer">
            <div class="d-flex flex-grow-1 overflow-hidden">
                <div class="pl-1" v-if="showSelection">
                    <b-check
                        class="selector"
                        :checked="selected"
                        @click.stop
                        @change="$emit('update:selected', $event)" />
                </div>

                <StatusIcon
                    v-if="dsc.state != 'ok'"
                    class="status-icon px-1"
                    :state="dsc.state"
                    @click.stop="onStatusClick" />

                <IconButton
                    v-if="!dsc.visible"
                    class="px-1"
                    state="hidden"
                    title="Unhide"
                    icon="eye-slash"
                    @click.stop="$emit('unhide')" />

                <IconButton
                    v-if="dsc.deleted"
                    class="px-1"
                    state="deleted"
                    title="Undelete"
                    icon="trash-restore"
                    @click.stop="$emit('undelete')" />

                <IconButton
                    class="px-1"
                    state="ok"
                    title="Collection"
                    icon="folder"
                    @click.stop="$emit('viewCollection')"
                    variant="link" />

                <div class="content-title title flex-grow-1 overflow-hidden" @click.stop="$emit('viewCollection')">
                    <h5 class="text-truncate">
                        <span class="hid">{{ dsc.hid }}</span>
                        <span class="name">{{ dsc.name }}</span>
                        <span class="description">
                            ({{ dsc.collectionType | localize }} {{ dsc.collectionCountDescription | localize }})
                        </span>
                    </h5>
                </div>
            </div>

            <div class="d-flex" v-if="writable">
                <slot name="menu">
                    <DscMenu v-if="!dsc.deleted" v-on="$listeners" :dsc="dsc" />
                </slot>
            </div>
        </nav>

        <!--- read-only tags with name: prefix -->
        <div v-if="collapsed && dsc.nameTags.length" class="nametags px-2 pb-2">
            <Nametag v-for="tag in dsc.nameTags" :key="tag" :tag="tag" />
        </div>

        <JobStateProgress class="m-2" v-if="dsc.jobSummary" :summary="dsc.jobSummary" />
    </div>
</template>

<script>
import { DatasetCollection } from "../../model/DatasetCollection";
import StatusIcon from "../../StatusIcon";
import JobStateProgress from "./JobStateProgress";
import DscMenu from "./DscMenu";
import { Nametag } from "components/Nametags";
import IconButton from "components/IconButton";

export default {
    components: {
        StatusIcon,
        JobStateProgress,
        DscMenu,
        Nametag,
        IconButton,
    },
    props: {
        dsc: { type: DatasetCollection, required: true },
        selected: { type: Boolean, required: false, default: false },
        showSelection: { type: Boolean, required: false, default: false },
        writable: { type: Boolean, required: false, default: true },
    },
    methods: {
        onStatusClick() {
            console.log("onStatusClick", ...arguments);
        },
    },
    computed: {
        typedId() {
            return this.dsc.type_id;
        },
        collapsed() {
            return !this.expanded;
        },
    },
};
</script>

<style lang="scss" scoped>
header,
header * {
    cursor: pointer;
}
</style>
