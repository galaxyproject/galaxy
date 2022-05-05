<template>
    <div>
        <b-link
            class="page-dropdown font-weight-bold"
            data-toggle="dropdown"
            aria-haspopup="true"
            :data-page-dropdown="page.id"
            aria-expanded="false">
            <font-awesome-icon icon="caret-down" />
            <span class="page-title">{{ page.title }}</span>
        </b-link>
        <p v-if="page.description">{{ page.description }}</p>
        <div class="dropdown-menu" aria-labelledby="page-dropdown">
            <a class="dropdown-item dropdown-item-view" :href="urlView">
                <span class="fa fa-eye fa-fw mr-1" />
                <span>View</span>
            </a>
            <a class="dropdown-item dropdown-item-edit" v-if="!readOnly" :href="urlEdit">
                <span class="fa fa-edit fa-fw mr-1" />
                <span>Edit Content</span>
            </a>
            <a class="dropdown-item dropdown-item-edit-attributes" v-if="!readOnly" :href="urlEditAttributes">
                <span class="fa fa-share-alt fa-fw mr-1" />
                <span>Edit Attributes</span>
            </a>
            <a class="dropdown-item dropdown-item-share" v-if="!readOnly" :href="urlShare">
                <span class="fa fa-share-alt fa-fw mr-1" />
                <span>Share</span>
            </a>
            <a class="dropdown-item" href="#" v-if="!readOnly" @click.prevent="onDelete">
                <span class="fa fa-trash fa-fw mr-1" />
                <span>Delete</span>
            </a>
        </div>
    </div>
</template>
<script>
import { Services } from "./services";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";

library.add(faCaretDown);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: ["page", "root"],
    computed: {
        urlEdit() {
            return `${this.root}page/edit_content?id=${this.page.id}`;
        },
        urlEditAttributes() {
            return `${this.root}page/edit?id=${this.page.id}`;
        },
        urlShare() {
            return `${this.root}pages/sharing?id=${this.page.id}`;
        },
        urlView() {
            return `${this.root}page/display_by_id?id=${this.page.id}`;
        },
        readOnly() {
            return !!this.page.shared;
        },
    },
    created() {
        this.services = new Services({ root: this.root });
    },
    methods: {
        onDelete() {
            const id = this.page.id;
            const name = this.page.title;
            const confirmationMessage = this.l(`Are you sure you want to delete page '${name}'?`);
            if (window.confirm(confirmationMessage)) {
                this.services
                    .deletePage(id)
                    .then((message) => {
                        this.$emit("onRemove", id);
                        this.$emit("onSuccess", message);
                    })
                    .catch((error) => {
                        this.$emit("onError", error);
                    });
            }
        },
    },
};
</script>
