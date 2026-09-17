import type { NextConfig } from "next";

const apiInternal = process.env.API_INTERNAL_URL || "http://127.0.0.1:5000";

const nextConfig: NextConfig = {
  output: "standalone",
  // Evita 308 `/socket.io/` → `/socket.io`, que quebrava o Engine.IO (POST do
  // polling não sobrevive bem ao redirect → "xhr poll error").
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiInternal}/api/v1/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${apiInternal}/uploads/:path*`,
      },
      {
        source: "/media/:path*",
        destination: `${apiInternal}/media/:path*`,
      },
      {
        source: "/api/registrar_push/:token",
        destination: `${apiInternal}/api/registrar_push/:token`,
      },
      {
        source: "/api/salvar_pedido/:token",
        destination: `${apiInternal}/api/salvar_pedido/:token`,
      },
      {
        source: "/api/verificar_senha/:token",
        destination: `${apiInternal}/api/verificar_senha/:token`,
      },
      {
        source: "/api/avaliar/:token",
        destination: `${apiInternal}/api/avaliar/:token`,
      },
      {
        source: "/api/vapid-public-key",
        destination: `${apiInternal}/api/vapid-public-key`,
      },
      // Destino com barra final: o middleware Engine.IO (WSGI) só atende `/socket.io/`.
      {
        source: "/socket.io",
        destination: `${apiInternal}/socket.io/`,
      },
      {
        source: "/socket.io/:path*",
        destination: `${apiInternal}/socket.io/:path*`,
      },
    ];
  },
};

export default nextConfig;
