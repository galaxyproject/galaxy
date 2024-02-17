import type { CodegenConfig } from '@graphql-codegen/cli'
 
const config: CodegenConfig = {
   schema: 'http://localhost:9009/graphql/',
   documents: ['src/**/*.vue', 'src/**/*.ts'],
   generates: {
      './src/gql/': {
        preset: 'client',
        plugins: [],
        config: {
            useTypeImport: true
        }
      }
   }
}
export default config
