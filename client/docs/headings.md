# Heading Levels and Sizing

Heading Levels are used by screen readers, and other software, to get a rough idea of the document structure, so it is important to keep this structure in mind when deciding on a headings level.

[Further reading on MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Heading_Elements)

## Heading Level best practices

-   Make sure every route has exactly one `<h1>` element, which best describes the content of the current page.

-   When increasing a heading level, do not skip Levels.

-   Do not use a headings level to determine it's size. Use one of the heading utility classes (e.g. `h-lg`) instead.

-   Do not use a heading tag to make a non-heading text large. Use a heading utility class on a `<span>` instead.

## Sizing Headings

There are several utility classes which size headings:

-   `h-xl` - Extra large headings
-   `h-lg` - Large headings (most main headings should have this size)
-   `h-md` - Medium headings
-   `h-sm` - Small headings (many sub-headings have this size)
-   `h-text` - Text sized headings

Galaxy uses `h-lg` for most top-level (`<h1>`) headings.

These sizes are purely visual, and do not necessarily have to follow the document structure.
It is fine to use several headings on the same page with the same heading level, and different sizes. An example for this would be the heading of an error message, which has a heading level of 2 (`<h2>`) in most cases, but is visually smaller than other sub-headings.

## Styling Headings with the `<Heading>` component

For more visually distinct headings, there is an `Heading` component, found under [`components/Common/Heading.vue`](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/Common/Heading.vue)

Make use of this component to break up flat layouts and add better separation to a page with multiple sections.

### Usage

Set the headings level, by setting aa `h1 ... h6` prop:

```vue
<Heading h1>Top Level Heading</Heading>
```

Following properties allow for further styling the component:

-   `size=["xl", "lg", "md", "sm", "text"]` - sets the headings size class
-   `bold` - makes a heading bold
-   `inline` - displays the heading inline
-   `separator` - draws a separating line, to better distinguish sections
-   `icon="..."` - adds a font-awesome icon decoration to the left of the heading. Make sure to also load the icon with `library.add(...)`.
