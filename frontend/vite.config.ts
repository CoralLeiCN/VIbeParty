import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("..", import.meta.url));
export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, root, ""), ...process.env };
  return {
    plugins: [react()],
    server: {
      port: Number(env.FRONTEND_PORT || 5173),
      strictPort: true,
      proxy: {
        "/api":
          env.API_PROXY_TARGET ||
          `http://127.0.0.1:${env.BACKEND_PORT || 8000}`,
        "/health": `http://127.0.0.1:${env.BACKEND_PORT || 8000}`,
      },
    },
  };
});
