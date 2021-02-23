/**
 * Functions for generating the sections for the style guide. Has the old style doc glob and a
 * recursive tree-walker that looks through the components folder and tries to arrange found
 * markdown docs in a tree.
 */

const path = require("path");
const fs = require("fs");
const glob = require("glob");
const { humanize, titleize } = require("underscore.string");

/**
 * Gets the table of contents sections for documentation in the components folder.
 *
 * @param   {string}  rootPath  absolute path to components folder
 * @return  {Object}            Rootnode, section map, childMap
 */
function getDocSections(rootPath, options = {}) {
    const { ignore = [], docSelector = "*.@(vue|md)" } = options;

    const sections = new Map(); // absolute section directory path -> section object
    const childToParent = new Map(); // absolute child path -> absolute parent path

    // create root node
    const rootNode = newSection(rootPath, ignore);
    sections.set(rootPath, rootNode);
    childToParent.set(rootPath, null);

    // get all matching doc files
    const selector = path.join(rootPath, "**", docSelector);
    const allFiles = glob.sync(selector, { ignore });

    allFiles.forEach((file) => {
        const p = path.parse(file);

        // intermediate dir names between this dir and root
        const relPath = path.relative(rootPath, p.dir);
        const midFolders = relPath.split(path.sep);

        // build intermediate parent sections in the event that this is deeply-nested
        while (midFolders.length) {
            const sectionPath = path.join(rootPath, ...midFolders);
            if (!sections.has(sectionPath)) {
                // create new section
                const section = newSection(sectionPath, ignore);
                sections.set(sectionPath, section);
                // register relationship for tree-build later
                const parentPath = path.join(sectionPath, "..");
                childToParent.set(sectionPath, parentPath);
            }
            midFolders.pop();
        }

        // if it's a MD file, add to parent as a subsection
        const section = sections.get(p.dir);
        if (section && isSubsection(section, file)) {
            section.children.add({
                name: titleize(humanize(p.name)),
                content: file,
            });
        }
    });

    // assemble recursive section tree under rootNode
    buildSectionTree(sections, childToParent);

    // rootNode is the main result, returning the maps so the user has the option to manipulate the
    // tree before handing it over to the styleguide configs
    return { sections, childToParent, rootNode };
}

function isSubsection(section, file) {
    const p = path.parse(file);

    // it's not a subsection if it's not a markdown file
    if (p.ext !== ".md") return false;

    // it's not a subsection if it's the same file as the section content
    if (file === section.content) return false;

    // it's not a subsection if it's an example for an existing component
    const matchingComponentPath = path.join(p.dir, `${p.name}.vue`);
    const componentExists = fs.existsSync(matchingComponentPath);
    if (componentExists) return false;

    return true;
}

/**
 * Creates a new section in the TOC from passed path.
 *
 * @param   {string}  dir  absolute directory path
 * @return  {Object}       section object
 */
function newSection(dir, ignore = []) {
    const section = {
        name: titleize(humanize(path.basename(dir))),
        components: () => glob.sync(path.join(dir, "*.vue"), { ignore }),
        children: new Set(),
        sectionDepth: 1,
    };

    // summary doc is readme/docs/index.md
    const summarySelector = path.join(dir, "@(readme|docs|index).md");
    const summaryDocs = glob.sync(summarySelector, { ignore, nocase: true });
    if (summaryDocs.length) {
        section.content = summaryDocs[0];
    }

    return section;
}

/**
 * Turns the pair of maps into a nested object for use in the styleguide config script. Operates on
 * sections array by reference.
 *
 * @param   {Map}  sections       Map of path -> section object
 * @param   {Map}  childToParent  Map of childPath -> parentPath
 */
function buildSectionTree(sections, childToParent) {
    // add each child to its parent
    for (const [childPath, parentPath] of childToParent) {
        const child = sections.get(childPath);
        const parent = sections.get(parentPath);
        if (child && parent && parent.children) {
            parent.children.add(child);
        }
    }
    // convert child Sets to arrays now that de-dupe not required
    for (const section of sections.values()) {
        section.sections = Array.from(section.children).sort((a, b) => a.name.localeCompare(b.name));
        delete section.children;
    }
}

module.exports = {
    // public function
    getDocSections,
    // exporting these in case user wants to tweak the result tree and rebuild it
    buildSectionTree,
    newSection,
};
