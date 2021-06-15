/**
 * Tests the functions which build the sections for the styleguide.
 */

const path = require("path");
const { getDocSections } = require("../sections");

const getSectionByName = (sections, name) => sections.find((o) => o.name == name);

describe("getDocSections", () => {
    const ignore = [
        // ignoring a whole directory
        "**/ignored/*",
        // ignoring a file
        "**/ignore*",
    ];
    const testDocRoot = path.join(__dirname, "sample-docs");
    const { rootNode } = getDocSections(testDocRoot, { ignore });

    test("section generation", () => {
        expect(rootNode.name).toEqual("Sample Docs");
        expect(rootNode.sections.length).toEqual(7);
        expect(rootNode.content).toBeUndefined();
    });

    test("nested subsection should appear even if no docs in intermediate folders", () => {
        const deepSection = getSectionByName(rootNode.sections, "Nested Folders");
        expect(deepSection.sections.length).toEqual(1);
    });

    test("subdirectory with readme should register as summary", () => {
        const subsection = getSectionByName(rootNode.sections, "Has Readme");

        // readme interpreted as content file and not as loose section
        // one other loose file
        expect(subsection.content).toContain("readme.md");
        expect(subsection.sections.length).toEqual(1);
    });

    test("subdirectory with no readme file", () => {
        const subsection = getSectionByName(rootNode.sections, "No Summary File");

        // should just see 2 folders no summary
        expect(subsection.content).toBeUndefined();
        expect(subsection.sections.length).toEqual(2);
    });

    test("subdirectory with ignored file", () => {
        const subsection = getSectionByName(rootNode.sections, "Contains Ommitted File");
        expect(subsection.sections.length).toEqual(1);
    });

    test("ignored subdirectory", () => {
        const ignoredSection = getSectionByName(rootNode.sections, "Ignored");
        expect(ignoredSection).toBeUndefined();
    });

    test("should not create a section for a component example file", () => {
        const section = getSectionByName(rootNode.sections, "Component Example");
        expect(section.sections.length).toEqual(0);
    });
});
