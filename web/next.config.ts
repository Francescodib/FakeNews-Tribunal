import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produce a self-contained server bundle so the Docker runtime stage
  // only needs node + the output of .next/standalone — no node_modules copy.
  output: "standalone",
};

export default nextConfig;
