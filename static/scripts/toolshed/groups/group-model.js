define("toolshed/groups/group-model", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });
    // ============================================================================
    // TS GROUP RELATED MODELS

    var Group = Backbone.Model.extend({
        urlRoot: Galaxy.root + "api/groups"
    });

    var Groups = Backbone.Collection.extend({
        url: Galaxy.root + "api/groups",

        model: Group
    });

    exports.default = {
        Group: Group,
        Groups: Groups
    };
});
//# sourceMappingURL=../../../maps/toolshed/groups/group-model.js.map
