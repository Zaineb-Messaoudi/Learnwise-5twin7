import { useState } from 'react';
import { Pause, Play, Volume2 } from 'lucide-react';
export function AudioPlayer() { const [playing, setPlaying] = useState(false); return <div className="audio-player"><button className="icon-button" aria-label={playing ? 'Pause audio' : 'Play audio'} onClick={() => setPlaying(!playing)}>{playing ? <Pause size={18}/> : <Play size={18}/>}</button><div className="audio-track"><span style={{ width: playing ? '46%' : '12%' }}/></div><span>12:46 / 18:42</span><Volume2 size={15}/></div>; }
