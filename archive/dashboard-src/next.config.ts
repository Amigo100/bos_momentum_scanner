import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Include the bundled data directory in the server build
  serverExternalPackages: ["papaparse"],
};

export default nextConfig;
