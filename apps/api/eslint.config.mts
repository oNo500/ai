import { GLOB_TESTS, composeConfig } from '@infra-x/eslint-config'
import { defineConfig } from 'eslint/config'

const API_TEST_FILES = [
  ...GLOB_TESTS,
  '**/*.e2e-spec.{js,mjs,cjs,jsx,ts,mts,cts,tsx}',
]

const baseConfig = composeConfig({
  jsdoc: true,
  typescript: {
    tsconfigRootDir: import.meta.dirname,
  },
  packageJson: {
    overrides: {
      'package-json/valid-devDependencies': 'off', // allow link: local dependencies
    },
  },
  // Module boundary checks: enforce VSA/DDD architecture rules (module isolation)
  boundaries: {
    elements: [
      // Module elements - capture module name for dependency validation
      {
        type: 'module',
        pattern: 'src/modules/*/**',
        capture: ['moduleName'],
        mode: 'folder',
      },
      // Shared kernel - code shared across modules
      {
        type: 'shared-kernel',
        pattern: 'src/shared-kernel/**',
        mode: 'folder',
      },
      // App layer - global infrastructure (middleware, config, filters)
      {
        type: 'app',
        pattern: 'src/app/**',
        mode: 'folder',
      },
      // Main entry files - application entry point and root module
      {
        type: 'main',
        pattern: ['src/main.ts', 'src/*.module.ts', 'src/*.d.ts'],
        mode: 'file',
      },
    ],
    rules: [
      // Default rule: modules may use shared-kernel and app
      {
        from: ['module'],
        allow: [
          'shared-kernel',
          'app',
          // Allow a module to import itself
          ['module', { moduleName: '${moduleName}' }],
        ],
        message: 'Cross-module imports are forbidden. Share code via shared-kernel or decouple through events.',
      },
      // Shared-kernel may use app infrastructure (pragmatic allowance)
      {
        from: ['shared-kernel'],
        allow: ['shared-kernel', 'app'],
        message: 'shared-kernel must not import business modules',
      },
      // App layer may use shared-kernel
      {
        from: ['app'],
        allow: ['app', 'shared-kernel'],
        message: 'The app layer should not directly depend on business modules',
      },
      // Main entry files may import all layers
      {
        from: ['main'],
        allow: ['module', 'shared-kernel', 'app', 'main'],
      },
    ],
  },
  unicorn: {
    overrides: {
      'unicorn/no-null': 'off', // Drizzle returns null; keep consistent
    },
  },
  imports: true,
})

const vitestConfig = defineConfig({
  files: API_TEST_FILES,
  extends: composeConfig({
    typescript: { tsconfigRootDir: import.meta.dirname },
    vitest: true,
    unicorn: false,
    stylistic: false,
    depend: false,
  }),
})

// Allow the auth module to depend on the profile and audit-log modules
const authBoundaryException = defineConfig({
  files: ['src/modules/auth/**/*.ts'],
  rules: {
    'boundaries/element-types': [
      'error',
      {
        default: 'disallow',
        rules: [
          {
            from: ['module'],
            allow: [
              'app',
              'shared-kernel',
              ['module', { moduleName: 'auth' }],
              ['module', { moduleName: 'profile' }],
              ['module', { moduleName: 'audit-log' }],
              'main',
            ],
          },
        ],
      },
    ],
  },
})

export default [...baseConfig, ...vitestConfig, ...authBoundaryException]
