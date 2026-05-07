import Vue from 'vue'
import VueRouter from 'vue-router'
import App from '../App.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'Home',
    component: App
  },
  {
    path: '/meeting/:id',
    name: 'Meeting',
    component: App
  }
]

const router = new VueRouter({
  mode: 'history',
  base: '/',
  routes
})

export default router
