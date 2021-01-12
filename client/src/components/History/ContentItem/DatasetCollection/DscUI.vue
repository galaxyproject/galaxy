<!-- UI only, updates/changes to data should be handled outside
    this component via events emissions -->

<template>
    <div
        class="dataset dataset-collection collapsed"
        :class="{ selected }"
        :data-state="dsc.state"
        @keydown.arrow-right.self.stop="$emit('select-collection', dsc)"
        @keydown.space.self.stop.prevent="$emit('update:selected', !selected)"
        @click.stop="
            $emit('select-collection', dsc);
            $emit('update:expanded', dsc);
        "
    >
        <nav class="d-flex content-top-menu align-items-center justify-content-between">
            <div class="d-flex mr-1 align-items-center" @click.stop>
                <b-check v-if="showSelection" :checked="selected" @change="$emit('update:selected', $event)" />

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
                    @click.stop="$emit('unhideCollection')"
                />

                <StateBtn
                    class="px-1"
                    state="ok"
                    title="Collection"
                    icon="fas fa-folder"
                    @click.stop="$emit('select-collection', dsc)"
                />
            </div>

            <h5 class="flex-grow-1 overflow-hidden mr-auto text-nowrap text-truncate">
                <span class="hid">{{ dsc.hid }}</span>
                <span class="name">{{ dsc.name }}</span>
                <span class="description">
                    ({{ dsc.collectionType | localize }} {{ dsc.collectionCountDescription | localize }})
                </span>
            </h5>

            <DscMenu v-if="!dsc.deleted" class="content-item-menu" v-on="$listeners" />
            <StateBtn
                v-if="dsc.deleted"
                class="px-1"
                state="deleted"
                title="Undelete"
                icon="fas fa-trash-restore"
                @click.stop="$emit('undeleteCollection')"
            />
        </nav>

        <JobStateProgress class="m-2" v-if="dsc.jobSummary" :summary="dsc.jobSummary" />
        <div v-else>No summary</div>
    </div>
</template>

<script>
import { DatasetCollection } from "../../model/DatasetCollection";
import { StatusIcon, StateBtn } from "../../StatusIcon";
import JobStateProgress from "./JobStateProgress";
import DscMenu from "./DscMenu";

export default {
    inject: ["listState", "STATES"],
    components: {
        StatusIcon,
        StateBtn,
        JobStateProgress,
        DscMenu,
    },
    props: {
        dsc: { type: DatasetCollection, required: true },
        selected: { type: Boolean, required: false, default: false },
        showHid: { type: Boolean, required: false, default: true },
    },
    computed: {
        counter() {
            return this.showHid ? this.dsc.hid : "";
        },
        showSelection() {
            return this.listState.showSelection;
        },
    },
    methods: {
        onStatusClick() {
            console.log("onStatusClick", ...arguments);
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
