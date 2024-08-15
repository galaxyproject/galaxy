### Default alert

```js
<Alert>An alert with all defaults</Alert>
```

### Alert variants

```js
<div v-for="variant in [ 'success', 'info', 'warning', 'error' ]">
    <Alert v-bind:variant="variant">A {{ variant }} message</Alert>
</div>
```

### Dismissible

```js
<div v-for="variant in [ 'success', 'info', 'warning', 'error' ]">
	<Alert :variant="variant" dismissible>A {{variant}} message</Alert>
</div>
```
