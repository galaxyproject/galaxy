import { createTag } from "./model";
import { TagService } from "./tagService";

// Some parts of the application save tags by saving model so that
// it will update other parts of the app, which is a rudimentary way
// of recreating reactivity, so I expect this will probably die soon

export class BackboneTagService extends TagService {
    constructor(props) {
        super(props);
        this.model = props.model;
    }

    async save(rawTag) {
        const tag = createTag(rawTag);
        if (!tag.valid) {
            throw new Error("Invalid tag");
        }

        // update model
        let tags = new Set(this.model.attributes.tags);
        tags.add(tag.text);
        tags = Array.from(tags);

        await this.model.save({ tags });
        return tag;
    }

    async delete(rawTag) {
        const tag = createTag(rawTag);

        let tags = new Set(this.model.attributes.tags);
        tags.delete(tag.text);
        tags = Array.from(tags);

        await this.model.save({ tags });
        return tag;
    }
}
