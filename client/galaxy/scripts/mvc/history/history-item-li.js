function _labelIfName(tag) {
    if (tag.indexOf("name:") == 0) {
        return `<span class="label label-info">${tag.slice(5)}</span>`;
    } else {
        return "";
    }
}

function nametagTemplate(historyItem) {
    return `<span class="nametags">${_.sortBy(_.uniq(historyItem.tags))
        .map(_labelIfName)
        .join("")}</span>`;
}

export default {
    nametagTemplate: nametagTemplate
};
