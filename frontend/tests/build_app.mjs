import { build } from "vite";
await build({ configFile: false, logLevel: "error", plugins: [(await import("@vitejs/plugin-react")).default()],
  build: { ssr: "src/App.jsx", outDir: "_ssr_app", rollupOptions: { output: { format: "esm" } } } });
