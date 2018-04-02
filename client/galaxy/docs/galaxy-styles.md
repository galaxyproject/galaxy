## Galaxy Styles

### Panel Messages

Messages that appear across the top of the panel view below the masthead.

```
<div>
  <div v-for="type in ['done', 'info', 'warning', 'error']">
    <div v-bind:class="'panel-' + type + '-message'">I'm a panel-{{type}}-message</div>
  </div>
</div>
```

### Large Messages

Used for providing feedback inline.

```
<div>
  <div v-for="type in ['done', 'info', 'warning', 'error']">
    <div v-bind:class="type + 'messagelarge'">I'm a {{type}}messagelarge</div>
  </div>
</div>
```

### Small Messages

```
<div>
  <div v-for="type in ['done', 'info', 'warning', 'error']">
    <div v-bind:class="type + 'message'">I'm a {{type}}message</div>
  </div>
</div>
```

## Buttons

```
<button>Just a default button</button>
```

```
<a href="#" class=action-button>An anchor with .action-button</a>
```

All the crazy permutations of menu button...

```
<a href="#" class=action-button>An anchor with .menu-button</a>
```

```
<a href="#" class=action-button>An anchor with .menu-button.popup</a>
```

```
<a href="#" class=action-button>An anchor with .menu-button.popup.split</a>
```

## Tables

Tables using the .grid class

```
<table class="grid">
  <thead class="grid-table-header">
    <tr><th>One</th><th>Two</th></tr>
  </thead>
  <tbody class="grid-table-body">
    <tr><td>Value 1</td><td>Value 2</td></tr>
  </tbody>
</table>
```
