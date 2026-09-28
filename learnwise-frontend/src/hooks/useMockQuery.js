import { useEffect, useState } from 'react';
export function useMockQuery(loader, initial) {
    const [data, setData] = useState(initial);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        let active = true;
        setLoading(true);
        loader().then(value => { if (active)
            setData(value); }).catch(reason => { if (active)
            setError(reason instanceof Error ? reason : new Error('Request failed')); }).finally(() => { if (active)
            setLoading(false); });
        return () => { active = false; };
    }, [loader]);
    return { data, loading, error, refetch: () => loader().then(setData) };
}
