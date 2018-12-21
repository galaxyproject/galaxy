## Buttons

Regular buttons

```vue
<div>
   <button type="button" class="btn btn-primary">Primary</button>
   <button type="button" class="btn btn-secondary">Secondary</button>
   <button type="button" class="btn btn-success">Success</button>
   <button type="button" class="btn btn-info">Info</button>
   <button type="button" class="btn btn-warning">Warning</button>
   <button type="button" class="btn btn-danger">Danger</button>
   <button type="button" class="btn btn-link">Link</button>
</div>
```

Disabled

```vue
<div>
   <button type="button" class="btn btn-primary disabled">Primary</button>
   <button type="button" class="btn btn-secondary disabled">Secondary</button>
   <button type="button" class="btn btn-success disabled">Success</button>
   <button type="button" class="btn btn-info disabled">Info</button>
   <button type="button" class="btn btn-warning disabled">Warning</button>
   <button type="button" class="btn btn-danger disabled">Danger</button>
   <button type="button" class="btn btn-link disabled">Link</button>
</div>
```

```vue
<div>
   <button type="button" class="btn btn-outline-primary">Primary</button>
   <button type="button" class="btn btn-outline-secondary">Secondary</button>
   <button type="button" class="btn btn-outline-success">Success</button>
   <button type="button" class="btn btn-outline-info">Info</button>
   <button type="button" class="btn btn-outline-warning">Warning</button>
   <button type="button" class="btn btn-outline-danger">Danger</button>
</div>
```

```vue
 <div class="btn-group" role="group" aria-label="Button group with nested dropdown">
   <button type="button" class="btn btn-primary">Primary</button>
   <div class="btn-group" role="group">
     <button id="btnGroupDrop1" type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"></button>
     <div class="dropdown-menu" aria-labelledby="btnGroupDrop1">
       <a class="dropdown-item" href="#">Dropdown link</a>
       <a class="dropdown-item" href="#">Dropdown link</a>
     </div>
   </div>
 </div>
```

```vue
 <div class="btn-group" role="group" aria-label="Button group with nested dropdown">
   <button type="button" class="btn btn-success">Success</button>
   <div class="btn-group" role="group">
     <button id="btnGroupDrop2" type="button" class="btn btn-success dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"></button>
     <div class="dropdown-menu" aria-labelledby="btnGroupDrop2">
       <a class="dropdown-item" href="#">Dropdown link</a>
       <a class="dropdown-item" href="#">Dropdown link</a>
     </div>
   </div>
 </div>
```

```vue
 <div class="btn-group" role="group" aria-label="Button group with nested dropdown">
   <button type="button" class="btn btn-info">Info</button>
   <div class="btn-group" role="group">
     <button id="btnGroupDrop3" type="button" class="btn btn-info dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"></button>
     <div class="dropdown-menu" aria-labelledby="btnGroupDrop3">
       <a class="dropdown-item" href="#">Dropdown link</a>
       <a class="dropdown-item" href="#">Dropdown link</a>
     </div>
   </div>
 </div>
```

```vue
   <div class="btn-group" role="group" aria-label="Button group with nested dropdown">
     <button type="button" class="btn btn-danger">Danger</button>
     <div class="btn-group" role="group">
       <button id="btnGroupDrop4" type="button" class="btn btn-danger dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"></button>
       <div class="dropdown-menu" aria-labelledby="btnGroupDrop4">
         <a class="dropdown-item" href="#">Dropdown link</a>
         <a class="dropdown-item" href="#">Dropdown link</a>
       </div>
     </div>
   </div>
 </div>
```

```vue
 <div>
   <button type="button" class="btn btn-primary btn-lg">Large button</button>
   <button type="button" class="btn btn-primary">Default button</button>
   <button type="button" class="btn btn-primary btn-sm">Small button</button>
 </div>
```

## Alerts

```vue
<div class="alert alert-dismissable alert-warning">
  <button type="button" class="close" data-dismiss="alert">&times;</button>
  <h4>Warning!</h4>
  <p>Best check yo self, you're not looking too good. Nulla vitae elit libero, a pharetra augue. Praesent commodo cursus magna, <a href="#" class="alert-link">vel scelerisque nisl consectetur et</a>.</p>
</div>
```

```vue
<div class="alert alert-dismissable alert-danger">
  <button type="button" class="close" data-dismiss="alert">&times;</button>
  <strong>Oh snap!</strong> <a href="#" class="alert-link">Change a few things up</a> and try submitting again.
</div>
```

```vue
<div class="alert alert-dismissable alert-success">
  <button type="button" class="close" data-dismiss="alert">&times;</button>
  <strong>Well done!</strong> You successfully read <a href="#" class="alert-link">this important alert message</a>.
</div>
```

```vue
<div class="alert alert-dismissable alert-info">
  <button type="button" class="close" data-dismiss="alert">&times;</button>
  <strong>Heads up!</strong> This <a href="#" class="alert-link">alert needs your attention</a>, but it's not super important.
</div>
```

## Badges

```vue
<div>
  <span class="badge badge-primary">Primary</span>
  <span class="badge badge-secondary">Secondary</span>
  <span class="badge badge-success">Success</span>
  <span class="badge badge-warning">Warning</span>
  <span class="badge badge-danger">Danger</span>
  <span class="badge badge-info">Info</span>
</div>
```

```vue
<div class="">
  <ul class="nav nav-pills">
    <li class="active"><a href="#">Home <span class="badge">42</span></a></li>
    <li><a href="#">Profile <span class="badge-pill"></span></a></li>
    <li><a href="#">Messages <span class="badge-pill">3</span></a></li>
  </ul>
</div>
```

## Tables

```vue
<div class="">
  <table class="table table-striped table-bordered table-hover">
    <thead>
      <tr>
        <th>#</th>
        <th>Column heading</th>
        <th>Column heading</th>
        <th>Column heading</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td>Column content</td>
        <td>Column content</td>
        <td>Column content</td>
      </tr>
      <tr>
        <td>2</td>
        <td>Column content</td>
        <td>Column content</td>
        <td>Column content</td>
      </tr>
      <tr>
        <td>3</td>
        <td>Column content</td>
        <td>Column content</td>
        <td>Column content</td>
      </tr>
      <tr class="table-success">
        <td>4</td>
        <td>Column content</td>
        <td>Column content</td>
        <td>Column content</td>
      </tr>
      <tr class="table-danger">
        <td>5</td>
        <td>Column content</td>
        <td>Column content</td>
        <td>Column content</td>
      </tr>
      <tr class="table-warning">
        <td>6</td>
        <td>Column content</td>
        <td>Column content</td>
        <td>Column content</td>
      </tr>
      <tr class="table-active">
        <td>7</td>
        <td>Column content</td>
        <td>Column content</td>
        <td>Column content</td>
      </tr>
    </tbody>
  </table>
</div>
```

## Cards

```vue
<div class="row">
  <div class="col-lg-4">
    <div class="bs-component">
      <div class="card text-white bg-primary mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Primary card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card text-white bg-secondary mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Secondary card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card text-white bg-success mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Success card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card text-white bg-danger mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Danger card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card text-white bg-warning mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Warning card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card text-white bg-info mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Info card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card bg-light mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Light card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card text-white bg-dark mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Dark card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
    </div>
  </div>
  <div class="col-lg-4">
    <div class="bs-component">
      <div class="card border-primary mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Primary card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card border-secondary mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Secondary card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card border-success mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Success card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card border-danger mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Danger card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card border-warning mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Warning card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card border-info mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Info card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card border-light mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Light card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
      <div class="card border-dark mb-3" style="max-width: 20rem;">
        <div class="card-header">Header</div>
        <div class="card-body">
          <h4 class="card-title">Dark card title</h4>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
      </div>
    </div>
  </div>

  <div class="col-lg-4">
    <div class="bs-component">
      <div class="card mb-3">
        <h3 class="card-header">Card header</h3>
        <div class="card-body">
          <h5 class="card-title">Special title treatment</h5>
          <h6 class="card-subtitle text-muted">Support card subtitle</h6>
        </div>
        <img style="height: 200px; width: 100%; display: block;" src="data:image/svg+xml;charset=UTF-8,%3Csvg%20width%3D%22318%22%20height%3D%22180%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%20318%20180%22%20preserveAspectRatio%3D%22none%22%3E%3Cdefs%3E%3Cstyle%20type%3D%22text%2Fcss%22%3E%23holder_158bd1d28ef%20text%20%7B%20fill%3Argba(255%2C255%2C255%2C.75)%3Bfont-weight%3Anormal%3Bfont-family%3AHelvetica%2C%20monospace%3Bfont-size%3A16pt%20%7D%20%3C%2Fstyle%3E%3C%2Fdefs%3E%3Cg%20id%3D%22holder_158bd1d28ef%22%3E%3Crect%20width%3D%22318%22%20height%3D%22180%22%20fill%3D%22%23777%22%3E%3C%2Frect%3E%3Cg%3E%3Ctext%20x%3D%22129.359375%22%20y%3D%2297.35%22%3EImage%3C%2Ftext%3E%3C%2Fg%3E%3C%2Fg%3E%3C%2Fsvg%3E" alt="Card image">
        <div class="card-body">
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
        </div>
        <ul class="list-group list-group-flush">
          <li class="list-group-item">Cras justo odio</li>
          <li class="list-group-item">Dapibus ac facilisis in</li>
          <li class="list-group-item">Vestibulum at eros</li>
        </ul>
        <div class="card-body">
          <a href="#" class="card-link">Card link</a>
          <a href="#" class="card-link">Another link</a>
        </div>
        <div class="card-footer text-muted">
          2 days ago
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <h4 class="card-title">Card title</h4>
          <h6 class="card-subtitle mb-2 text-muted">Card subtitle</h6>
          <p class="card-text">Some quick example text to build on the card title and make up the bulk of the card's content.</p>
          <a href="#" class="card-link">Card link</a>
          <a href="#" class="card-link">Another link</a>
        </div>
      </div>
    </div>
  </div>
</div>
```
