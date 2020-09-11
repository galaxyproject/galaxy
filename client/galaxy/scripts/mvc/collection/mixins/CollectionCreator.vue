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
                        <div v-if="isExpanded"> 
                            <i class="fas fa-chevron-up"></i>
                        </div>
                    </a>
                </div>
            </div>
            <!-- <div class="alert alert-dismissable">
                <button type="button" class="close" data-dismiss="alert" :title="titleMoreHelp" aria-hidden="true">
                    &times;
                </button>
            </div> -->
        </div>
        <div class="middle flex-row flex-row-container">
            <slot name="middle-content"></slot>
        </div>
        <div class="footer flex-row no-flex">
            <div class="attributes clear">
                <div class="clear">
                    <label class="setting-prompt float-right">
                        {{ buttonClearText }}
                        <input class="hide-originals float-right" type="checkbox" />
                    </label>
                </div>
                <div class="clear">
                    <input class="collection-name form-control float-right" :placeholder="placeholderEnterName" />
                    <div class="collection-name-prompt float-right">
                        {{ l("Name:") }}
                    </div>
                </div>
            </div>
            <div class="actions clear vertically-spaced">
                <div class="other-options float-left">
                    <button class="cancel-create btn" tabindex="-1">
                        {{ l("Cancel") }}
                    </button>
                    <div class="create-other btn-group dropup">
                        <!-- <button class="btn btn-secondary dropdown-toggle" data-toggle="dropdown">
                            {{ l("Create a different kind of collection") }}
                            <span class="caret"></span>
                        </button> -->
                        <b-dropdown text="l('Create a different kind of collection')">
                            <b-dropdown-item> {{ l("Create a <i>single</i> pair") }} </b-dropdown-item>
                        </b-dropdown>
                        <!-- <div class="dropdown-menu" role="menu">
                            <a class="dropdown-item" href="javascript:void(0)" role="button">
                                {{ l("Create a <i>single</i> pair") }}
                            </a>
                        </div> -->
                    </div>
                </div>
                <div class="main-options float-right">
                    <button class="create-collection btn btn-primary">
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
    data: function () {
        return {
            titleForHelp: _l("Expand or Close Help"),
            titleMoreHelp: _l("Close and show more help"),
            placeholderEnterName: _l("Enter a name for your new collection"),
            dropdownText: _l("Create a <i>single</> pair"),
            isExpanded: false,
        };
    },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
        // ........................................................................ header
        /** expand help */
        _clickForHelp: function () {
            this.isExpanded = !this.isExpanded;
            return this.isExpanded;
        },
    },
};
</script>
