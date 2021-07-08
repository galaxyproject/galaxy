<template>
    <div class="collection-menu">
        <PriorityMenu :starting-height="27">
            <PriorityMenuItem
                v-if="notIn(STATES.DISCARDED)"
                key="restructure-collection"
                :title="restructureButtonTitle"
                icon="fas fa-project-diagram"
                @click.stop="restructureShow = !restructureShow"
            >
            </PriorityMenuItem>
            <PriorityMenuItem
                v-if="notIn(STATES.DISCARDED)"
                key="edit-collection"
                :title="deleteCollectionButtonTitle"
                @click.stop="deleteCollectionModalShow = !deleteCollectionModalShow"
                icon="fas fa-trash"
            >
            </PriorityMenuItem>
        </PriorityMenu>
        <b-modal v-model="deleteCollectionModalShow" @ok="runDelete(deleteSelected)">
            <b-form-group label="Select a method to delete the collection">
                <b-form-radio v-model="deleteSelected" name="delete-select" :value="null"
                    >Delete Collection Only</b-form-radio
                >
                <b-form-radio v-model="deleteSelected" name="delete-select" :value="{ recursive: true }"
                    >Delete Contained Datasets</b-form-radio
                >
                <b-form-radio v-model="deleteSelected" name="delete-select" :value="{ recursive: true, purge: true }"
                    >Purge Contained Datasets</b-form-radio
                >
            </b-form-group>
        </b-modal>
        <b-modal v-model="restructureShow" hide-footer :title="restructureTitle">
            <Restructure v-if="restructureShow" :collection="collection" />
        </b-modal>
    </div>
</template>

<script>
import Restructure from "./Restructure";
import { DatasetCollection } from "../../model";
import { PriorityMenu, PriorityMenuItem } from "components/PriorityMenu";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);
export default {
    data() {
        return {
            deleteSelected: null,
            deleteCollectionModalShow: false,
            restructureShow: false,
        };
    },
    components: {
        PriorityMenu,
        PriorityMenuItem,
        Restructure,
    },
    mixins: [legacyNavigationMixin],
    inject: ["STATES"],
    props: {
        collection: { type: DatasetCollection, required: true },
    },
    computed: {
        deleteCollectionButtonTitle() {
            return "Delete Collection";
        },
        restructureButtonTitle() {
            return "Restructure Collection";
        },
        restructureTitle() {
            return `Restructure ${this.collection.name}`;
        },
    },
    methods: {
        runDelete: function (kind) {
            if (kind) {
                this.$emit("delete", kind);
            } else {
                this.$emit("delete");
            }
        },
        collectionEditURL: function () {
            return "/collection/edit/" + this.collection.hdca_id;
        },
        notIn(...states) {
            const badStates = new Set(states);
            return !badStates.has(this.collection.state);
        },
        isIn(...states) {
            const goodStates = new Set(states);
            return goodStates.has(this.collection.state);
        },
    },
};
</script>
