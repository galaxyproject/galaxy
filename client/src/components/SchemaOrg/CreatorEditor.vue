<template>
    <span class="creators-editor">
        <div v-if="editIndex != null && creatorsCurrent[editIndex].class == 'Person'">
            <PersonForm :person="creatorsCurrent[editIndex]" @onSave="onSave" @onReset="onCancel" />
        </div>
        <div v-else-if="editIndex != null && creatorsCurrent[editIndex].class == 'Organization'">
            <OrganizationForm :organization="creatorsCurrent[editIndex]" @onSave="onSave" @onReset="onCancel" />
        </div>
        <div v-else-if="creatorsCurrent">
            <div v-for="(creator, index) in creatorsCurrent" :key="index">
                <CreatorViewer :creator="creator">
                    <template v-slot:buttons>
                        <BButton
                            v-b-tooltip.hover
                            class="inline-icon-button"
                            variant="link"
                            size="sm"
                            title="编辑创建者"
                            @click="onEdit(index)">
                            <FontAwesomeIcon icon="edit" />
                        </BButton>
                        <BButton
                            v-b-tooltip.hover
                            class="inline-icon-button"
                            variant="link"
                            size="sm"
                            title="移除创建者"
                            @click="onRemove(index)">
                            <FontAwesomeIcon icon="times" />
                        </BButton>
                    </template>
                </CreatorViewer>
            </div>
        </div>
        <div>
            <i>
                添加新创建者 - 可以是
                <a href="#" @click.prevent="editNewPerson()">个人</a>
                或 <a href="#" @click.prevent="editNewOrganization()">机构</a>。
            </i>
        </div>
    </span>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import CreatorViewer from "./CreatorViewer";
import OrganizationForm from "./OrganizationForm";
import PersonForm from "./PersonForm";

library.add(faTimes);
library.add(faEdit);

export default {
    components: {
        FontAwesomeIcon,
        PersonForm,
        CreatorViewer,
        OrganizationForm,
    },
    props: {
        creators: {
            type: Array,
            default: () => [],
        },
    },
    data() {
        return {
            creatorsCurrent: [],
            editIndex: null,
        };
    },
    watch: {
        creators: {
            handler(newCreators) {
                this.creatorsCurrent = newCreators;
            },
            immediate: true,
        },
    },
    methods: {
        onEdit(index) {
            this.editIndex = index;
        },
        onRemove(index) {
            const creators = [...this.creatorsCurrent];
            creators.splice(index, 1);
            this.$emit("onCreators", creators);
        },
        onSave(creator) {
            const index = this.editIndex;
            const creators = [...this.creatorsCurrent];
            creators[index] = creator;
            this.$emit("onCreators", creators);
            this.editIndex = null;
        },
        onCancel() {
            const index = this.editIndex;
            const creator = this.creatorsCurrent[index];
            if (creator.isNew) {
                this.creatorsCurrent.splice(index, 1);
            }
            this.editIndex = null;
        },
        editNewPerson() {
            this.creatorsCurrent.push({ class: "Person", isNew: true, name: "", identifier: "" });
            this.editIndex = this.creatorsCurrent.length - 1;
        },
        editNewOrganization() {
            this.creatorsCurrent.push({ class: "Organization", isNew: true, name: "" });
            this.editIndex = this.creatorsCurrent.length - 1;
        },
    },
};
</script>
