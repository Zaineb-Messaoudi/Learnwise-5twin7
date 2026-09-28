import { useRef, useState } from 'react';
import { AlertCircle, Check, CloudUpload, FileText, RotateCcw } from 'lucide-react';
import { mockApi } from '../../mocks/mockApi';
import { isBackendApiEnabled } from '../../api/client';
import { materialsApi } from '../../api/materials.api';
import { useToast } from './Toast';
const maxFileSize = 250 * 1024 * 1024;
const processingLabels = { queued: 'Waiting in processing queue', processing: 'Processing course material', completed: 'Processing complete', failed: 'Processing failed' };

export function FileUploader({ courseId }) {
    const inputRef = useRef(null);
    const [file, setFile] = useState(null);
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('idle');
    const [error, setError] = useState('');
    const [materialId, setMaterialId] = useState(null);
    const { notify } = useToast();
    const select = async (next, retry = false) => {
        if (!next)
            return;
        const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'audio/mpeg', 'audio/wav', 'audio/x-wav'];
        const allowedExtensions = /\.(pdf|docx|mp3|wav)$/i;
        if (!allowedExtensions.test(next.name) || (next.type && !allowedTypes.includes(next.type))) {
            setError('Choose a PDF, DOCX, MP3, or WAV file.');
            setStatus('failed');
            return;
        }
        if (next.size > maxFileSize) {
            setError('This file exceeds the 250 MiB limit. Choose a smaller file.');
            setStatus('failed');
            return;
        }
        if (isBackendApiEnabled && !courseId) {
            setError('Choose a course before uploading this material.');
            setStatus('failed');
            return;
        }
        setFile(next);
        setError('');
        setProgress(0);
        setStatus('uploading');
        try {
            let result;
            if (isBackendApiEnabled) {
                result = retry && materialId
                    ? await materialsApi.retryProcessing(materialId)
                    : await materialsApi.upload(courseId, next, { kind: next.type.startsWith('audio/') ? 'audio' : 'document' }, event => {
                        if (event.total) setProgress(Math.round(event.loaded / event.total * 100));
                    });
                if (result.id) setMaterialId(result.id);
                if (result.progress != null) setProgress(result.progress);
                setStatus(result.status || 'queued');
                if (result.id && ['queued', 'processing'].includes(result.status)) {
                    for (let attempt = 0; attempt < 30; attempt += 1) {
                        await new Promise(resolve => window.setTimeout(resolve, 2000));
                        result = await materialsApi.processingStatus(result.id);
                        if (result.progress != null) setProgress(result.progress);
                        setStatus(result.status);
                        if (['completed', 'failed'].includes(result.status)) break;
                    }
                }
                if (result.status === 'failed') throw new Error(result.error_message || 'Processing failed. Retry the material or upload another file.');
                if (result.status !== 'completed') {
                    notify('Upload accepted. Processing continues in the background.', 'info');
                    return;
                }
                setProgress(100);
                notify(`${next.name} processed successfully`, 'success');
            } else {
                result = await mockApi.uploadMaterial(next);
                setProgress(result.progress);
                setStatus('completed');
                notify(`${next.name} is selected locally. Transcription and processing require the service connection.`, 'info');
            }
        } catch (cause) {
            setStatus('failed');
            setError(cause instanceof Error ? cause.message : 'Upload failed. Check your connection and retry.');
            notify('The material could not be uploaded. Review the error and retry.', 'error');
        }
    };
    const busy = ['uploading', 'queued', 'processing'].includes(status);
    return <div className="local-uploader" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); void select(event.dataTransfer.files[0]); }}><input ref={inputRef} type="file" name="course-material" accept=".pdf,.mp3,.wav,.docx,application/pdf,audio/mpeg,audio/wav" hidden onChange={event => { void select(event.target.files?.[0]); event.target.value = ''; }}/>{file ? <><div className="upload-file"><FileText size={22}/><div><b>{file.name}</b><span>{status === 'completed' && !isBackendApiEnabled ? 'File selected · Ready to review' : status === 'completed' ? 'Transcription and summary ready' : processingLabels[status] || `Uploading ${progress}%`}</span></div>{status === 'completed' ? <Check size={18}/> : status === 'failed' ? <AlertCircle size={18}/> : null}</div>{status !== 'failed' && <div className="progress-track" role="progressbar" aria-label="Material upload and processing" aria-valuenow={progress} aria-valuemin="0" aria-valuemax="100"><div className="progress-value" style={{ width: `${progress}%` }}/></div>}{error && <p className="upload-error" role="alert">{error}</p>}{status === 'failed' && <button type="button" className="button button-secondary" onClick={() => void select(file, true)}><RotateCcw size={15}/> Retry upload</button>}</> : <><div className="upload-icon"><CloudUpload size={24}/></div><h3>Drop course material here</h3><p>PDF, audio, or DOCX up to 250 MiB</p><button type="button" className="button button-secondary" onClick={() => inputRef.current?.click()}>Choose a file</button></>}</div>;
}
