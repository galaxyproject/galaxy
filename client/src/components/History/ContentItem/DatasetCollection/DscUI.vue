<!-- UI only, updates/changes to data should be handled outside
    this component via events emissions -->

<template>
    <div
        class="dataset dataset-collection collapsed"
        :class="{ selected }"
        :id="typedId"
        :data-state="dsc.state"
        @keydown.arrow-right.self.stop="$emit('viewCollection')"
        @keydown.space.self.stop.prevent="$emit('update:selected', !selected)"
        @click.stop="$emit('viewCollection')"
    >
        <nav class="content-top-menu">
            <div class="content-status-indicators mr-1" @click.stop>
                <b-check
                    class="selector"
                    v-if="showSelection"
                    :checked="selected"
                    @change="$emit('update:selected', $event)"
                />

                <StatusIcon
                    v-if="dsc.state != 'ok'"
                    class="status-icon px-1"
                    :state="dsc.state"
                    @click.stop="onStatusClick"
                />

                <StateBtn
                    v-if="!dsc.visible"
                    class="px-1"
                    state="hidden"
                    title="Unhide"
                    icon="fa fa-eye-slash"
                    @click.stop="$emit('unhide')"
                />

                <StateBtn
                    v-if="dsc.deleted"
                    class="px-1"
                    state="deleted"
                    title="Undelete"
                    icon="fas fa-trash-restore"
                    @click.stop="$emit('undelete')"
                />

                <StateBtn
                    class="px-1"
                    state="ok"
                    title="Collection"
                    icon="fas fa-folder"
                    @click.stop="$emit('viewCollection')"
                />
            </div>

            <div class="content-title mr-1">
                <h5 class="text-truncate">
                    <span class="hid">{{ dsc.hid }}</span>
                    <span class="name">{{ dsc.name }}</span>
                    <span class="description">
                        ({{ dsc.collectionType | localize }} {{ dsc.collectionCountDescription | localize }})
                    </span>
                </h5>
            </div>

            <div class="content-item-menu">
                <slot name="menu">
                    <DscMenu v-if="!dsc.deleted" v-on="$listeners" />
                </slot>
            </div>
        </nav>

        <!--- read-only tags with name: prefix -->
        <div v-if="dsc.nameTags.length" class="nametags p-1">
            <Nametag v-for="tag in dsc.nameTags" :key="tag" :tag="tag" />
        </div>

        <JobStateProgress class="m-2" v-if="dsc.jobSummary" :summary="dsc.jobSummary" />
    </div>
</template>

<script>
import { DatasetCollection } from "../../model/DatasetCollection";
import { StatusIcon, StateBtn } from "../../StatusIcon";
import JobStateProgress from "./JobStateProgress";
import DscMenu from "./DscMenu";
import { Nametag } from "components/Nametags";

export default {
    components: {
        StatusIcon,
        StateBtn,
        JobStateProgress,
        DscMenu,
        Nametag,
    },
    props: {
        dsc: { type: DatasetCollection, required: true },
        selected: { type: Boolean, required: false, default: false },
        showSelection: { type: Boolean, required: false, default: false },
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
    },
};
</script>

<style lang="scss" scoped>
header,
header * {
    cursor: pointer;
}
</style>
