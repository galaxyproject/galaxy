function _labelIfName(tag) {
    if (tag.indexOf("name:") === 0) {
        return `<span class="label label-info">${_.escape(tag.slice(5))}</span>`;
    } else {
        return "";
    }
}

function nametagTemplate(historyItem) {
    let nametags = _.sortBy(_.uniq(historyItem.tags)).map(_labelIfName);
    return `
        <div class="nametags" title="${nametags.length} nametags">
            ${nametags.join("")}
        </div>`;
}

export default {
    nametagTemplate: nametagTemplate
};
