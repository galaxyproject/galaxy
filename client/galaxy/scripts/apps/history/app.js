import React from  'react';
import {render} from 'react-dom';
import Main from './components/Main';

window.app = function app(options, bootstrapped) {
    render(<Main />, document.getElementById('everything'));
}
