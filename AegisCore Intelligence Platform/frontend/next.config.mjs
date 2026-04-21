/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",

  // Security headers for all routes
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          // Strict-Transport-Security (HSTS) - forces HTTPS
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains; preload",
          },
          // Content-Security-Policy - prevents XSS and injection attacks
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline'", // Required for Next.js
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              "font-src 'self'",
              "connect-src 'self' http://localhost:8000 https:", // API calls
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "upgrade-insecure-requests",
            ].join("; "),
          },
          // X-Content-Type-Options - prevents MIME sniffing
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          // X-Frame-Options - prevents clickjacking
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          // X-XSS-Protection - legacy XSS protection
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          // Referrer-Policy - limits referrer information
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          // Permissions-Policy - restricts browser features
          {
            key: "Permissions-Policy",
            value: [
              "accelerometer=()",
              "camera=()",
              "geolocation=()",
              "gyroscope=()",
              "magnetometer=()",
              "microphone=()",
              "payment=()",
              "usb=()",
              "interest-cohort=()", // Disable FLoC
            ].join(", "),
          },
          // X-DNS-Prefetch-Control - disable DNS prefetching
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
