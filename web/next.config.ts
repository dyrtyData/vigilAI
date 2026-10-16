import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async redirects() {
    return [{ source: "/pt-br", destination: "/", permanent: true }];
  },
  async rewrites() {
    // Serve the statically generated Portuguese page without a locale prefix.
    return [{ source: "/", destination: "/pt-br" }];
  },
};

export default nextConfig;
