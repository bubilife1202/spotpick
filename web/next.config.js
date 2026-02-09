/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    proxyTimeout: 120_000, // 기본 30초 → 120초 (AI 사업계획서 생성에 ~50초 소요)
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8002/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
