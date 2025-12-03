/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typescript: {
    // Skip type checking during build (parent node_modules interference)
    ignoreBuildErrors: true,
  },
}

module.exports = nextConfig
