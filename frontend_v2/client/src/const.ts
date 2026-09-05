export { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";

// Generate login URL at runtime so redirect URI reflects the current origin.
export const getLoginUrl = () => {
  const oauthPortalUrl = import.meta.env.VITE_OAUTH_PORTAL_URL;
  const appId = import.meta.env.VITE_APP_ID;
  const redirectUri = `${window.location.origin}/api/oauth/callback`;
  const state = btoa(redirectUri);

  const url = new URL(`${oauthPortalUrl}/app-auth`);
  url.searchParams.set("appId", appId);
  url.searchParams.set("redirectUri", redirectUri);
  url.searchParams.set("state", state);
  url.searchParams.set("type", "signIn");

  return url.toString();
};

export const DOMAIN_COLORS: Record<string, {
  hex: number;
  str: string;
  text: string;
  border: string;
  bg: string;
  activeBorder: string;
  colorClass: string;
  hoverClass: string;
  gradient: string;
}> = {
  customer_care: {
    hex: 0xfbbf24,
    str: '#fbbf24',
    text: 'text-amber-500',
    border: 'border-amber-500/30',
    bg: 'bg-amber-500/5',
    activeBorder: 'border-amber-500',
    colorClass: 'text-amber-500 border-amber-500/30 bg-amber-500/5',
    hoverClass: 'hover:bg-amber-500/10',
    gradient: 'from-amber-500 to-yellow-400'
  },
  social: {
    hex: 0xc026d3,
    str: '#c026d3',
    text: 'text-fuchsia-500',
    border: 'border-fuchsia-500/30',
    bg: 'bg-fuchsia-500/5',
    activeBorder: 'border-fuchsia-500',
    colorClass: 'text-fuchsia-500 border-fuchsia-500/30 bg-fuchsia-500/5',
    hoverClass: 'hover:bg-fuchsia-500/10',
    gradient: 'from-fuchsia-500 to-pink-500'
  },
  finance: {
    hex: 0x2dd4bf,
    str: '#2dd4bf',
    text: 'text-teal-400',
    border: 'border-teal-400/30',
    bg: 'bg-teal-400/5',
    activeBorder: 'border-teal-400',
    colorClass: 'text-teal-400 border-teal-400/30 bg-teal-400/5',
    hoverClass: 'hover:bg-teal-400/10',
    gradient: 'from-teal-400 to-emerald-400'
  },
  management: {
    hex: 0x60a5fa,
    str: '#60a5fa',
    text: 'text-blue-400',
    border: 'border-blue-400/30',
    bg: 'bg-blue-400/5',
    activeBorder: 'border-blue-400',
    colorClass: 'text-blue-400 border-blue-400/30 bg-blue-400/5',
    hoverClass: 'hover:bg-blue-400/10',
    gradient: 'from-blue-500 to-cyan-400'
  },
  general: {
    hex: 0x64748b,
    str: '#64748b',
    text: 'text-slate-400',
    border: 'border-slate-500/20',
    bg: 'bg-slate-500/5',
    activeBorder: 'border-slate-500',
    colorClass: 'text-slate-400 border-slate-500/20 bg-slate-500/5',
    hoverClass: 'hover:bg-slate-500/10',
    gradient: 'from-slate-500 to-gray-400'
  }
};

// Aliases for compatibility
(DOMAIN_COLORS as any).customer = DOMAIN_COLORS.customer_care;
