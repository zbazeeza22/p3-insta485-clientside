import js from "@eslint/js";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";
import { importX } from "eslint-plugin-import-x";
import cypress from "eslint-plugin-cypress";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import prettierPlugin from "eslint-config-prettier/flat";
import globals from "globals";

export default [
  // Ignore all files matching these glob patterns
  {
    ignores: [
      "**/node_modules/**",
      "**/build/**",
      "**/dist/**",
      "**/coverage/**",
      "**/*.min.js",
      "**/bundle.js",
      "**/deployed_bundle.js",
    ],
  },

  // Configure files that run in node separately
  {
    files: ["**/cypress.config.js", "**/webpack.config.js"],
    languageOptions: {
      ecmaVersion: "latest",
      // CommonJS configs are scripts, not ESM modules
      sourceType: "script",
      globals: {
        ...globals.node, // gives you require, module, process, __dirname, etc.
        ...globals.es2022,
      },
    },
  },

  // Base JavaScript/JSX configuration
  {
    files: ["**/*.js", "**/*.jsx"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.es2022,
      },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      "import-x": importX,
    },
    settings: {
      react: {
        version: "detect",
      },
      "import-x/resolver": {
        node: {
          extensions: [".js", ".jsx", ".ts", ".tsx"],
        },
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      ...importX.flatConfigs.recommended.rules,

      // Custom rules
      "no-var": "error",
      "no-console": 0,
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      "react/prop-types": "off",
      "react/no-typos": "off",
    },
  },

  // Cypress test files configuration
  {
    files: ["**/*.cy.js", "**/cypress/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2022,
      },
    },
    plugins: {
      cypress,
    },
    ...cypress.configs.recommended,
    rules: {
      "no-var": "error",
      "no-console": 0,
      "cypress/no-pause": "error",
    },
  },

  // TypeScript configuration
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.es2022,
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      react,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      "import-x": importX,
    },
    settings: {
      react: {
        version: "detect",
      },
      "import-x/resolver": {
        node: {
          extensions: [".js", ".jsx", ".ts", ".tsx"],
        },
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      ...importX.flatConfigs.recommended.rules,
      ...importX.flatConfigs.typescript.rules,
      ...tsPlugin.configs.recommended.rules,

      // Custom rules
      "no-var": "error",
      "no-console": 0,
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react/prop-types": "off",
    },
  },

  prettierPlugin,
];
