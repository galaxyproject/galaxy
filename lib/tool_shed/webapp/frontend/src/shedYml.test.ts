import { describe, expect, it } from "vitest"
import { shedYml } from "./shedYml"

const repository = {
    name: "bismark",
    owner: "devteam",
    type: "unrestricted",
    description: "Bisulfite mapper",
    long_description: null,
}

describe("shedYml", () => {
    it("writes the keys planemo reads, in .shed.yml's usual order", () => {
        const yml = shedYml(
            {
                ...repository,
                long_description: "Maps bisulfite reads.\n\nSee the manual.",
                homepage_url: "https://www.bioinformatics.babraham.ac.uk/projects/bismark/",
                remote_repository_url: "https://github.com/galaxyproject/tools-iuc/tree/main/tools/bismark",
            },
            ["Sequence Analysis", "Next Gen Mappers"],
        )

        expect(yml).toBe(`name: bismark
owner: devteam
description: Bisulfite mapper
long_description: |-
  Maps bisulfite reads.

  See the manual.
homepage_url: https://www.bioinformatics.babraham.ac.uk/projects/bismark/
remote_repository_url: https://github.com/galaxyproject/tools-iuc/tree/main/tools/bismark
type: unrestricted
categories:
- Sequence Analysis
- Next Gen Mappers
`)
    })

    it("leaves out settings the repository doesn't have", () => {
        expect(shedYml({ ...repository, homepage_url: null }, [])).toBe(`name: bismark
owner: devteam
description: Bisulfite mapper
type: unrestricted
`)
    })

    it("quotes values YAML would read as something else", () => {
        const yml = shedYml({ ...repository, description: "Mapper: fast #1" }, ["yes", "2024-01-01"])

        expect(yml).toContain('description: "Mapper: fast #1"')
        expect(yml).toContain('categories:\n- "yes"\n- "2024-01-01"\n')
    })

    it("quotes what a literal block or plain scalar can't hold exactly", () => {
        const yml = shedYml(
            { ...repository, long_description: "Windows\r\nline endings", homepage_url: "https://example.org/x:" },
            ["Odd\u007fname"],
        )

        expect(yml).toContain('long_description: "Windows\\r\\nline endings"')
        expect(yml).toContain('homepage_url: "https://example.org/x:"')
        expect(yml).toContain('- "Odd\\u007fname"')
    })
})
