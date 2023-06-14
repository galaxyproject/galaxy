# Custom Icons

Enables loading external and custom made icons into the `FontAwesomeIcon` component.
This has the advantage of using a common interface and feature set for all icons.

Use cases for custom icons are:

-   The free font-awesome library does not have a fitting icon
-   A font awesome icon is not clear enough for the intended purpose
-   A variant for an icon is required, which is not included in font awesome free

Avoid using custom icons in all other cases when possible.

## Folder Structure

If the icon is fully custom (e.g. you, or another galaxy contributor made the icon), place it in the `galaxy` sub-folder.

Otherwise create a new sub-folder with the name of the icon-pack you are importing this icon from.
In order for this pack to load, you will also need to specify it in `icon-packs.json`.
Make sure to include license and repository information.

## File Naming

Icon files need to be named in the following pattern: `[name].[variant].svg`

`[name]` will be the name your icon can later be accessed by.
`[variant]` can either be `solid`, `regular`, or `duotone`.

You can have several icons with the same name, and different variants.
These can then be loaded by specifying the right prefix.

Example:

-   The icon pack galaxy has the prefix `gx`
-   It includes an icon called `magnet.duotone.svg`
-   The icon can be used using `<FontAwesomeIcon :icon="['gxd', 'magnet']" />`
-   The `d` in `gxd` is for duotone

## File Structure

SVG files need to follow a certain structure in order to be usable by Font-Awesome-Vue.
Make sure your icon:

-   Has no transforms. Most SVG applications allow for "flattening transforms" on export. This will remove any transforms from your SVG file
-   Has one (or two for duotone) paths. Styles will be ignored, so make sure the path alone shows your icon. If you have an icon which utilizes outlines/strokes, expand the stroke before export
-   Has a width and height property

## Icon List

`all-icons.md` contains a list of all custom icons.

It is auto-generated from the same data as the output icon pack.
If an icon is included in this list, you can use it in your code.
