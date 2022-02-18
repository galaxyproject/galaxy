<!-- Edits a collection, if that collection is editable. -->

<template>
    <section class="history-details d-flex" data-description="edit details">
        <div class="flex-grow-1">
            <h3 class="history-title" data-description="collection name display">
                {{ dscName || "(Collection Name)" }}
            </h3>
            <p class="mt-1">
                <Description :dsc="dsc" />
            </p>

            <div v-if="isEditing" class="mt-3" @keydown.esc="revertAndCancel" data-description="edit form">
                <b-textarea
                    v-model="dscName"
                    placeholder="Collection Name"
                    trim
                    max-rows="4"
                    data-description="name input"></b-textarea>
                <StatelessTags v-model="tags" class="mt-3 tags" />
            </div>

            <div v-else-if="dsc.tags && dsc.tags.length">
                <Nametag v-for="tag in dsc.tags" :key="tag" :tag="tag" />
            </div>
        </div>

        <EditorMenu
            class="ml-3 flex-grow-0 d-flex flex-column"
            v-if="writeable"
            model-name="Collection"
            :editing.sync="editing"
            :writeable="writeable"
            :valid="valid"
            :dirty="dirty"
            @save="save"
            @revert="revert" />
    </section>
</template>

<script>
import { DatasetCollection } from "components/History/model";
import { Nametag } from "components/Nametags";
import EditorMenu from "components/History/EditorMenu";
import { StatelessTags } from "components/Tags";
import Description from "./Description";

export default {
    components: {
        Nametag,
        EditorMenu,
        StatelessTags,
        Description,
    },
    props: {
        dsc: { type: Object, required: true },
        writeable: { type: Boolean, required: true },
    },
    data() {
        return {
            editing: false,
            tempContent: Object.assign({}, this.dsc),
        };
    },
    computed: {
        dscId() {
            return this.dsc.id;
        },
        isEditing() {
            return this.writeable && this.editing;
        },
        valid() {
            return this.tempContent.name.length > 0;
        },
        dirty() {
            return !this.tempContent.equals(this.dsc);
        },
        dscName: {
            get() {
                return this.tempContent.name;
            },
            set(newName) {
                this.patchTempDsc({ name: newName });
            },
        },
        tags: {
            get() {
                return this.tempContent?.tags || [];
            },
            set(newTags) {
                if (Array.isArray(newTags)) {
                    this.patchTempDsc({ tags: newTags });
                }
            },
        },
    },
    watch: {
        dscId(newId, oldId) {
            if (newId != oldId) {
                this.reset();
            }
        },
    },
    methods: {
        reset() {
            this.tempContent = Object.assign({}, this.dsc);
        },
        patchTempDsc(props = {}) {
            this.tempContent = this.tempContent.patch(props);
        },
        save() {
            if (this.valid) {
                this.$emit("update:dsc", this.tempContent);
                this.editing = false;
            }
        },
        revert() {
            if (this.dirty) {
                this.reset();
            }
        },
        revertAndCancel() {
            this.revert();
            this.editing = false;
        },
    },
};
</script>
