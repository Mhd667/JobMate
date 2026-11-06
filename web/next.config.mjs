/** @type {import('next').NextConfig} */
// The site forwards /api/* to the backend, so a phone on the same Wi-Fi only needs the site's address.
const backend = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
};
export default nextConfig;
