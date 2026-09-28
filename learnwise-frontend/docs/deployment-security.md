# Frontend deployment headers

`public/_headers` configures browser security headers for static deployments that
support the Netlify/Cloudflare Pages `_headers` format. Confirm that the selected
hosting provider applies this file to both the app shell and deep-link routes.
Other hosts need equivalent response-header rules in their own configuration.

The Content Security Policy permits same-origin scripts, inline styles used by
the current React/CSS layouts, HTTPS API connections, secure WebSockets, and
same-origin camera/microphone use for the voice workflows. If an API, asset, or
media service uses a separate origin, add only that exact origin to the relevant
CSP directive before deployment.

HSTS is appropriate only when the production site is served over HTTPS and all
subdomains support HTTPS. The backend/API host must configure its own security
headers; this file only applies to the frontend static host.
