/**
 * Utility functions to detect the current environment
 */

/**
 * Check if the app is running on localhost
 */
export function isLocalhost(): boolean {
  if (typeof window === 'undefined') {
    return false; // Server-side rendering
  }

  const hostname = window.location.hostname;

  return (
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '[::1]' ||
    hostname.startsWith('192.168.') ||
    hostname.startsWith('10.') ||
    hostname.includes('local')
  );
}

/**
 * Check if the app is running on the hosted Vercel site
 */
export function isHostedSite(): boolean {
  return !isLocalhost();
}
