import React from 'react';
import { Link } from 'react-router-dom';
import { PublicSectionPage } from '../../../pages/PublicPages';

export function LegalPage({ type }) { const privacy = type === 'privacy'; return <PublicSectionPage title={privacy ? 'Privacy, explained clearly.' : 'Terms for using Learnwise.'} description={privacy ? 'Learnwise is designed to keep your learning journey personal and your account information protected.' : 'Use Learnwise to organize course materials, ask questions, practice, and follow your learning progress.'}><p><Link className="text-link" to="/auth/register">Back to account creation</Link></p></PublicSectionPage>; }
