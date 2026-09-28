import React from 'react';
import { Link } from 'react-router-dom';
import './public-shell.css';

export function BrandMark({ className = 'brand-mark' }) {
  return <Link className={className} to="/" aria-label="Learnwise home">
    <img src="/assets/learnwise-wordmark.png" width="512" height="115" alt="Learnwise" />
    <img className="brand-symbol-only" src="/assets/learnwise-symbol.png" width="96" height="82" alt="" aria-hidden="true" />
  </Link>;
}
