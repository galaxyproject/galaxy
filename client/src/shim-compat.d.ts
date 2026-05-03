declare module '@vue/compat' {
  import { Component, App, Plugin } from 'vue'
  export function configureCompat(options: Record<string, any>): void
  export * from 'vue'
}