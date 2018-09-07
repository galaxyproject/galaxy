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
