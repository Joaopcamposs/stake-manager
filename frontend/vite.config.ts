import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

export default defineConfig({
  base: "/static/dist/",
  plugins: [tailwindcss()],
  build: {
    outDir: resolve(__dirname, "../static/dist"),
    emptyOutDir: true,
    cssMinify: true,
    manifest: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "src/main.ts"),
      },
      output: {
        entryFileNames: "js/[name]-[hash].js",
        chunkFileNames: "js/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash].[ext]",
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/bets": "http://localhost:8000",
      "/dashboard": "http://localhost:8000",
    },
  },
});
