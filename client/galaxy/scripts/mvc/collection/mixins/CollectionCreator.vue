<template>
    <div>
        <div class="header flex-row no-flex">
            <div class="main-help well clear">
                <a class="more-help" href="javascript:void(0);" role="button">
                    _l("More help")
                </a>
                <div class="help-content">
                    <!-- each collection that extends this will add their own help content -->
                    <slot name="help-content"></slot>
                    <a class="less-help" href="javascript:void(0);" role="button"> _l("Less")_ </a>
                    <span class="alert-message"></span>
                </div>
            </div>
            <div class="alert alert-dismissable">
                <button type="button" class="close" data-dismiss="alert" title="titleMoreHelp" aria-hidden="true">
                    &times;
                </button>
            </div>
        </div>
        <div class="middle flex-row flex-row-container">
            <slot name="middle-content"></slot>
        </div>
        <div class="footer flex-row no-flex">
            <div class="attributes clear">
                <div class="clear">
                    <label class="setting-prompt float-right">
                        _l("Hide original elements") ?
                        <input class="hide-originals float-right" type="checkbox" />
                    </label>
                </div>
                <div class="clear">
                    <input class="collection-name form-control float-right" placeholder="placeholderEnterName" />
                    <div class="collection-name-prompt float-right">
                        _l("Name"):
                    </div>
                </div>
            </div>
            <div class="actions clear vertically-spaced">
                <div class="other-options float-left">
                    <button class="cancel-create btn" tabindex="-1">
                        _l("Cancel")
                    </button>
                    <div class="create-other btn-group dropup">
                        <button class="btn btn-secondary dropdown-toggle" data-toggle="dropdown">
                            _l("Create a different kind of collection")
                            <span class="caret"></span>
                        </button>
                        <div class="dropdown-menu" role="menu">
                            <a class="dropdown-item" href="javascript:void(0)" role="button">
                                _l("Create a <i>single</i> pair")
                            </a>
                        </div>
                    </div>
                </div>
                <div class="main-options float-right">
                    <button class="create-collection btn btn-primary">
                        _l("Create list")
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>
<script>
export default {
    
}
</script>