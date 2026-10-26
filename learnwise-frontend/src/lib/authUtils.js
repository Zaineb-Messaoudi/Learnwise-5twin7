/** Best human-readable message from an axios/DRF error: `detail`, then the first field error. */
export function errorMessage(cause, fallback = 'Something went wrong. Please try again.') {
    const data = cause?.response?.data;
    if (typeof data === 'string' && data.length < 300 && !data.trim().startsWith('<')) return data;
    if (data?.detail) return String(data.detail);
    if (data && typeof data === 'object') {
        const buckets = [data.errors, data];
        for (const bucket of buckets) {
            if (!bucket || typeof bucket !== 'object') continue;
            for (const [field, value] of Object.entries(bucket)) {
                const first = Array.isArray(value) ? value[0] : value;
                if (typeof first === 'string') return field === 'non_field_errors' || field === 'detail' ? first : `${field.replaceAll('_', ' ')}: ${first}`;
            }
        }
    }
    if (cause?.response?.status === 429) return 'Too many attempts. Please wait a moment and try again.';
    return cause?.message && !/status code/i.test(cause.message) ? cause.message : fallback;
}

/** Only same-site paths are valid post-login destinations (blocks `?next=https://evil.example`). */
export function safeNextPath(value, fallback = '') {
    if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return fallback;
    if (value.startsWith('/auth/login') || value.startsWith('/auth/register') || value.startsWith('/auth/social-callback')) return fallback;
    return value;
}
