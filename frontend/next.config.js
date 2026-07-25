/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: '500mb',
    },
  },
  async rewrites() {
    const apiUrl = process.env.INTERNAL_API_URL || 'http://reels-api:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
      {
        source: '/webhook',
        destination: `${apiUrl}/webhook`,
      },
    ]
  },
}

module.exports = nextConfig
