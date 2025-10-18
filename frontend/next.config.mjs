/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,  // 개발 환경에서 Strict Mode 비활성화
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
