import { getArgs, parseMarkdown, replaceLabel, splitMarkdown } from "./parse";

describe("parse.ts", () => {
    describe("getArgs", () => {
        it("parses simple directive expression", () => {
            const args = getArgs("job_metrics(job_id=THISFAKEID)");
            expect(args.name).toBe("job_metrics");
        });

        it("parses labels spaces at the end with single quotes", () => {
            const args = getArgs("job_metrics(step=' fakestepname ')");
            expect(args.name).toBe("job_metrics");
            expect(args.args.step).toBe(" fakestepname ");
        });

        it("parses labels spaces at the end with double quotes", () => {
            const args = getArgs('job_metrics(step=" fakestepname ")');
            expect(args.name).toBe("job_metrics");
            expect(args.args.step).toBe(" fakestepname ");
        });
    });

    describe("parseSections", () => {
        it("strip leading whitespace by default", () => {
            const sections = parseMarkdown(
                "```galaxy\njob_metrics(job_id=THISFAKEID)\n```\n DEFAULT_CONTENT \n```special\n SPECIAL_CONTENT \n```\n MORE_DEFAULT_CONTENT"
            );
            expect(sections.length).toBe(4);
            expect(sections[0].name).toBe("galaxy");
            expect(sections[0].content).toBe("job_metrics(job_id=THISFAKEID)");
            expect(sections[1].name).toBe("markdown");
            expect(sections[1].content).toBe("DEFAULT_CONTENT");
            expect(sections[2].name).toBe("special");
            expect(sections[2].content).toBe("SPECIAL_CONTENT");
            expect(sections[3].name).toBe("markdown");
            expect(sections[3].content).toBe("MORE_DEFAULT_CONTENT");
        });
    });

    describe("splitMarkdown", () => {
        it("strip leading whitespace by default", () => {
            const { sections } = splitMarkdown("\n```galaxy\njob_metrics(job_id=THISFAKEID)\n```");
            expect(sections.length).toBe(1);
        });

        it("should not strip leading whitespace if disabled", () => {
            const { sections } = splitMarkdown("\n```galaxy\njob_metrics(job_id=THISFAKEID)\n```", true);
            expect(sections.length).toBe(2);
            expect(sections[0].content).toBe("\n");
        });

        it("should parse labels with leading spaces", () => {
            const { sections } = splitMarkdown("\n```galaxy\njob_metrics(step='THISFAKEID ')\n```", true);
            expect(sections.length).toBe(2);
            expect(sections[0].content).toBe("\n");
        });
    });

    describe("replaceLabel", () => {
        it("should leave unaffected markdown alone", () => {
            const input = "some random\n`markdown content`\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(result);
        });

        it("should leave unaffected galaxy directives alone", () => {
            const input = "some random\n`markdown content`\n```galaxy\ncurrent_time()\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(result);
        });

        it("should leave galaxy directives of same type with other labels alone", () => {
            const input = "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(output=moo)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(result);
        });

        it("should leave galaxy directives of other types with same labels alone", () => {
            const input = "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(input=from)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(result);
        });

        it("should swap simple directives of specified type", () => {
            const input = "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(output=from)\n```\n";
            const output = "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(output=to)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(output);
        });

        it("should swap single quoted directives of specified type", () => {
            const input = "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(output='from')\n```\n";
            const output = "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(output=to)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(output);
        });

        it("should swap single quoted directives of specified type with extra args", () => {
            const input =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output='from', title=dog)\n```\n";
            const output =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output=to, title=dog)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(output);
        });

        it("should swap double quoted directives of specified type", () => {
            const input = 'some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(output="from")\n```\n';
            const output = "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(output=to)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(output);
        });

        it("should swap double quoted directives of specified type with extra args", () => {
            const input =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output=\"from\", title=dog)\n```\n";
            const output =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output=to, title=dog)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(output);
        });

        it("should work with double quotes for labels and spaces in the quotes", () => {
            const input =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output=\"from this\", title=dog)\n```\n";
            const output =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output=\"to that\", title=dog)\n```\n";
            const result = replaceLabel(input, "output", "from this", "to that");
            expect(result).toBe(output);
        });

        it("should work with single quotes for labels and spaces in the quotes", () => {
            const input =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output='from this', title=dog)\n```\n";
            const output =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output='to that', title=dog)\n```\n";
            const result = replaceLabel(input, "output", "from this", "to that");
            expect(result).toBe(output);
        });

        it("should work with single quotes for labels and spaces in the quotes including end", () => {
            const input =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output='from this ', title=dog)\n```\n";
            const output =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output='to thatx ', title=dog)\n```\n";
            const result = replaceLabel(input, "output", "from this ", "to thatx ");
            expect(result).toBe(output);
        });

        it("should add quotes when refactoring to labels with spaces", () => {
            const input =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output=fromthis, title=dog)\n```\n";
            const output =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output='to that', title=dog)\n```\n";
            const result = replaceLabel(input, "output", "fromthis", "to that");
            expect(result).toBe(output);
        });

        it("should add quotes when refactoring to labels with spaces including end space", () => {
            const input =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output=fromthis, title=dog)\n```\n";
            const output =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(footer='cow', output='to that ', title=dog)\n```\n";
            const result = replaceLabel(input, "output", "fromthis", "to that ");
            expect(result).toBe(output);
        });

        it("should leave non-arguments alone", () => {
            const input =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(title='cow from farm', output=from)\n```\n";
            const output =
                "some random\n`markdown content`\n```galaxy\nhistory_dataset_embedded(title='cow from farm', output=to)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(output);
        });

        // not a valid workflow label per se but make sure we're escaping the regex to be safe
        it("should not be messed up by labels containing regexp content", () => {
            const input = "```galaxy\nhistory_dataset_embedded(output='from(')\n```\n";
            const output = "```galaxy\nhistory_dataset_embedded(output=to$1)\n```\n";
            const result = replaceLabel(input, "output", "from(", "to$1");
            expect(result).toBe(output);
        });

        it("should not swallow leading newlines", () => {
            const input = "\n```galaxy\nhistory_dataset_embedded(output='from')\n```\n";
            const output = "\n```galaxy\nhistory_dataset_embedded(output=to)\n```\n";
            const result = replaceLabel(input, "output", "from", "to");
            expect(result).toBe(output);
        });
    });
});
