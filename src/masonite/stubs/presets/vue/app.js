/**
 * First we will load all of this project's JavaScript dependencies which
 * includes Vue and other libraries. It is a great starting point when
 * building robust, powerful web applications using Vue and Masonite.
 */

import './bootstrap.js'
import '../css/app.css'

import { createApp } from 'vue'
import App from './App.vue'

/**
 * Next, we will create a fresh Vue application instance
 */
const app = createApp(App)

/**
 * You can register components manually:
 *
 * import ExampleComponent from './components/ExampleComponent.vue'
 * app.component('example-component', ExampleComponent)
 */

/**
 * Finally we attach the Vue instance to the page. Then, you may begin
 * adding components to this application or customize the JavaScript
 * scaffolding to fit your unique needs.
 */

app.mount('#app')
