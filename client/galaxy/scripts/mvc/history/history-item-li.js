function _templateNametag(tag) {
    return `<span style="background-color: ${generateTagColor(tag.slice(5))}" class="badge badge-primary badge-tags">${_.escape(tag.slice(5))}</span>`;
}

function generateTagColor(tagValue) {
    var hash = hashFnv32a(tagValue);
    var r = ((hash & 0xf) % 10),
        g = (((hash & 0xf0) >> 4) % 10),
        b = (((hash & 0xf00) >> 8) % 10);

    return `#${r}${g}${b}`;
}

function nametagTemplate(historyItem) {
    let uniqueNametags = _.filter(_.uniq(historyItem.tags), t => t.indexOf("name:") === 0);
    let nametagsDisplay = _.sortBy(uniqueNametags).map(_templateNametag);
    return `
        <div class="nametags" title="${uniqueNametags.length} nametags">
            ${nametagsDisplay.join("")}
        </div>`;
}

export default {
    nametagTemplate: nametagTemplate
};

/**
 * Calculate a 32 bit FNV-1a hash
 * Found here: https://gist.github.com/vaiorabbit/5657561
 * Ref.: http://isthe.com/chongo/tech/comp/fnv/
 *
 * @param {string} str the input value
 * @returns {integer}
 */
function hashFnv32a(str) {
    /*jshint bitwise:false */
    var i, l,
        hval = 0x811c9dc5;

    for (i = 0, l = str.length; i < l; i++) {
        hval ^= str.charCodeAt(i);
        hval += (hval << 1) + (hval << 4) + (hval << 7) + (hval << 8) + (hval << 24);
    }
    return hval >>> 0;
}
