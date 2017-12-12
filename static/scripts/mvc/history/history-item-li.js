define("mvc/history/history-item-li", ["exports"], function(exports) {
    "use strict";

    Object.defineProperty(exports, "__esModule", {
        value: true
    });

    function _labelIfName(tag) {
        if (tag.indexOf("name:") == 0) {
            return "<span class=\"label label-info\">" + _.escape(tag.slice(5)) + "</span>";
        } else {
            return "";
        }
    }

    function nametagTemplate(historyItem) {
        return "<span class=\"nametags\">" + _.sortBy(_.uniq(historyItem.tags)).map(_labelIfName).join("") + "</span>";
    }

    exports.default = {
        nametagTemplate: nametagTemplate
    };
});
//# sourceMappingURL=../../../maps/mvc/history/history-item-li.js.map
