import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Button, DataTable } from '../../../components/shared/Primitives';

export function StaffActivity({ teacher = false, activity, backend = false }) {
  return <section className="table-card"><div className="section-title"><div><span className="eyebrow">{teacher ? 'RECENT ACTIVITY' : 'SYSTEM ACTIVITY'}</span><h2>{teacher ? 'Latest learner activity' : 'Recent activity'}</h2></div>{!backend && <Button variant="ghost">View all <ArrowRight size={14}/></Button>}</div>{backend ? activity?.length ? <div className="data-table-wrap"><table><thead><tr><th>{teacher ? 'Learner' : 'Actor'}</th><th>Activity</th><th>Module</th><th>When</th></tr></thead><tbody>{activity.map((item, index) => <tr key={item.id || index}><td>{item.actor_name || item.user_name || 'Learner'}</td><td>{item.action || item.title || item.activity_type}</td><td>{item.module || 'Learning'}</td><td>{item.created_at ? new Date(item.created_at).toLocaleString() : 'Recently'}</td></tr>)}</tbody></table></div> : <p className="state-panel">No recent activity is available for this period.</p> : <DataTable teacher={teacher}/>}</section>;
}
