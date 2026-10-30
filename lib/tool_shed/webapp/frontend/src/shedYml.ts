import { type components } from "@/schema"

type ShedYmlRepository = Pick<
    components["schemas"]["DetailedRepository"],
    | "name"
    | "owner"
    | "type"
    | "description"
    | "long_description"
    | "homepage_url"
    | "remote_repository_url"
    | "categories"
>

// Left plain only when YAML would read it back as the same string, otherwise JSON's quoting is valid YAML.
// Starting with a letter rules out numbers, dates and indicators; booleans and null are the words left.
const PLAIN_SCALAR = /^[A-Za-z][\w ./()+,-]*$|^https?:\/\/[^\s#]*[^\s#:]$/
const RESOLVES_TO_NON_STRING = /^(true|false|yes|no|on|off|y|n|null)$/i
// Characters YAML refuses, or reads as line breaks, unescaped. JSON.stringify escapes the C0 ones itself.
// eslint-disable-next-line no-control-regex -- matching control characters is the point
const UNPRINTABLE = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u2028\u2029\ufffe\uffff]/

function quoted(value: string): string {
    return JSON.stringify(value).replace(
        new RegExp(UNPRINTABLE, "g"),
        (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`,
    )
}

function scalar(value: string): string {
    if (PLAIN_SCALAR.test(value) && !RESOLVES_TO_NON_STRING.test(value) && !value.endsWith(" ")) {
        return value
    }
    return quoted(value)
}

// A literal block keeps a multi-line description readable; anything it can't hold exactly is quoted
function block(value: string): string {
    if (!value.includes("\n")) {
        return scalar(value)
    }
    if (/^\s|\r|\n\n$/.test(value) || UNPRINTABLE.test(value)) {
        return quoted(value)
    }
    const chomp = value.endsWith("\n") ? "|" : "|-"
    const lines = value.replace(/\n$/, "").split("\n")
    return `${chomp}\n${lines.map((line) => (line ? `  ${line}` : "")).join("\n")}`
}

// The .shed.yml planemo would create or update this repository from. Planemo never uploads the file
// itself, so it is rebuilt from the repository's settings.
export function shedYml(repository: ShedYmlRepository): string {
    const lines = [
        `name: ${scalar(repository.name)}`,
        `owner: ${scalar(repository.owner)}`,
        `description: ${scalar(repository.description)}`,
    ]
    if (repository.long_description) {
        lines.push(`long_description: ${block(repository.long_description)}`)
    }
    if (repository.homepage_url) {
        lines.push(`homepage_url: ${scalar(repository.homepage_url)}`)
    }
    if (repository.remote_repository_url) {
        lines.push(`remote_repository_url: ${scalar(repository.remote_repository_url)}`)
    }
    lines.push(`type: ${scalar(repository.type)}`)
    if (repository.categories.length > 0) {
        lines.push("categories:", ...repository.categories.map((category) => `- ${scalar(category.name)}`))
    }
    return `${lines.join("\n")}\n`
}
