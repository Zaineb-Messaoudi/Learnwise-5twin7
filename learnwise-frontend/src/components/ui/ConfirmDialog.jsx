import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

export function ConfirmDialog({ open, title, message, onConfirm, onClose }) {
  const dialogRef = useRef(null);
  const triggerRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    if (!open) return undefined;
    triggerRef.current = document.activeElement;
    const background = document.querySelector('.app-shell');
    const wasInert = background?.inert ?? false;
    if (background) background.inert = true;
    const dialog = dialogRef.current;
    const focusable = [...dialog.querySelectorAll('button, a[href], input, textarea, select')];
    focusable[0]?.focus();
    const close = event => {
      if (event.key === 'Escape') onCloseRef.current();
      if (event.key === 'Tab' && focusable.length) {
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('keydown', close);
      if (background) background.inert = wasInert;
      if (triggerRef.current?.isConnected && !wasInert) triggerRef.current.focus?.();
    };
  }, [open]);
  if (!open) return null;
  return createPortal(<div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}><div ref={dialogRef} className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title" aria-describedby="dialog-message"><button className="icon-button dialog-close" onClick={onClose} aria-label="Close dialog"><X size={17} /></button><h2 id="dialog-title">{title}</h2><p id="dialog-message">{message}</p><div className="dialog-actions"><button className="button button-secondary" onClick={onClose}>Cancel</button><button className="button" onClick={onConfirm}>Confirm</button></div></div></div>, document.body);
}
