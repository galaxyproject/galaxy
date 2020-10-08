<template>
    <div class="collection-creator">
        <div class="header flex-row no-flex">
            <div class="main-help well clear" v-bind:class="{ expanded: isExpanded }">
                <a
                    class="more-help"
                    href="javascript:void(0);"
                    role="button"
                    @click="_clickForHelp"
                    :title="titleForHelp"
                >
                    <div v-if="!isExpanded">
                        <i class="fas fa-chevron-down"></i>
                    </div>
                    <div v-else>
                        <i class="fas fa-chevron-up"></i>
                    </div>
                </a>
                <div class="help-content">
                    <!-- each collection that extends this will add their own help content -->
                    <slot name="help-content"></slot>
                    <a
                        class="more-help"
                        href="javascript:void(0);"
                        role="button"
                        @click="_clickForHelp"
                        :title="titleForHelp"
                    >
                    </a>
                </div>
            </div>
        </div>
        <div class="middle flex-row flex-row-container">
            <slot name="middle-content"></slot>
        </div>
        <div class="footer flex-row no-flex">
            <div class="attributes clear">
                <div class="clear">
                    <label class="setting-prompt float-right">
                        {{ hideOriginalsText }}
                        <input
                            class="hide-originals float-right"
                            type="checkbox"
                            @click="$emit('hide-original-toggle')"
                        />
                    </label>
                </div>
                <div class="clear">
                    <input
                        class="collection-name form-control float-right"
                        :placeholder="placeholderEnterName"
                        v-model="collectionName"
                    />
                    <div class="collection-name-prompt float-right">
                        {{ l("Name:") }}
                    </div>
                </div>
            </div>
            <div class="actions clear vertically-spaced">
                <div class="float-left">
                    <button class="cancel-create btn" tabindex="-1" @click="_cancelCreate">
                        {{ l("Cancel") }}
                    </button>
                    <div class="other-options create-other btn-group dropup">
                        <button class="btn btn-secondary dropdown-toggle" data-toggle="dropdown">
                            {{ l("Create a different kind of collection") }}
                            <span class="caret"></span>
                        </button>
                    </div>
                </div>
                <div class="main-options float-right">
                    <button
                        class="create-collection btn btn-primary"
                        @click="$emit('clicked-create', collectionName)"
                        :disabled="!validInput"
                    >
                        {{ l("Create list") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import _l from "utils/localization";
export default {
    props: {
        oncancel: {
            type: Function,
            required: true,
        },
        creationFn: {
            type: Function,
            required: true,
        },
    },
    computed: {
        validInput: function () {
            return this.collectionName.length > 0;
        },
    },
    data: function () {
        return {
            titleForHelp: _l("Expand or Close Help"),
            hideOriginalsText: _l("Hide original elements?"),
            titleMoreHelp: _l("Close and show more help"),
            placeholderEnterName: _l("Enter a name for your new collection"),
            dropdownText: _l("Create a <i>single</> pair"),
            isExpanded: false,
            collectionName: "",
        };
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        _clickForHelp: function () {
            this.isExpanded = !this.isExpanded;
            return this.isExpanded;
        },
        _cancelCreate: function () {
            this.oncancel();
        },
        _getName: function () {
            return this.collectionName;
        },
        _setUpCommonSettings: function (attributes) {
            this.hideOriginals = attributes.defaultHideSourceItems || false;
        },
    },
};
</script>
