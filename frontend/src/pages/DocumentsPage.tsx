import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, Trash2 } from 'lucide-react';
import { DocumentItem } from '../types';
import { fetchDocuments, uploadDocument, deleteDocument, subscribeToDocumentEvents } from '../api/documents';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const list = await fetchDocuments();
      setDocuments(list);
    } catch {
      // ignore
    }
  };

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setUploadError(null);
    setIsUploading(true);

    try {
      const res = await uploadDocument(file);
      // Refresh list to include newly queued document
      await loadDocuments();

      // Subscribe to SSE progress for this upload
      subscribeToDocumentEvents(
        res.document_id,
        (status, progress) => {
          setDocuments((prev) =>
            prev.map((d) => (d.id === res.document_id ? { ...d, status, progress } : d))
          );
        },
        () => {
          setDocuments((prev) =>
            prev.map((d) =>
              d.id === res.document_id ? { ...d, status: 'COMPLETED', progress: 100 } : d
            )
          );
          setIsUploading(false);
        },
        (err) => {
          setDocuments((prev) =>
            prev.map((d) =>
              d.id === res.document_id ? { ...d, status: 'FAILED', error: err } : d
            )
          );
          setIsUploading(false);
        }
      );
    } catch (err: any) {
      setUploadError(err.message || 'File upload failed');
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document from the vector store?')) return;
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch {
      // ignore
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900">Document Management</h2>
        <p className="text-sm text-slate-500 mt-1">
          Seed research papers and user-uploaded files indexed into ChromaDB.
        </p>
      </div>

      {/* Upload Dropzone */}
      <div
        onClick={() => fileInputRef.current?.click()}
        className="border-2 border-dashed border-slate-300 hover:border-indigo-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-white hover:bg-slate-50"
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={(e) => handleFileUpload(e.target.files)}
          accept=".pdf,.txt,.md"
          className="hidden"
        />
        <div className="flex flex-col items-center justify-center space-y-2">
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center">
            <Upload className="w-6 h-6" />
          </div>
          <span className="text-sm font-semibold text-slate-800">
            Click to upload or drag and drop
          </span>
          <span className="text-xs text-slate-500">
            Supported formats: PDF, TXT, Markdown (Max 50 MB)
          </span>
        </div>
      </div>

      {uploadError && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-lg text-sm flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Documents Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-800">
            Indexed Documents ({documents.length})
          </h3>
          <button
            onClick={loadDocuments}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
          >
            Refresh list
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs text-left">
              <tr>
                <th className="px-6 py-3 font-medium">Document</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Size</th>
                <th className="px-6 py-3 font-medium">Source</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {documents.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-400">
                    No documents found.
                  </td>
                </tr>
              )}
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-50">
                  <td className="px-6 py-3.5 flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    <span className="font-medium text-slate-900 truncate max-w-sm">
                      {doc.filename}
                    </span>
                  </td>
                  <td className="px-6 py-3.5 text-slate-500 uppercase text-xs font-mono">
                    {doc.file_type.replace('.', '')}
                  </td>
                  <td className="px-6 py-3.5 text-slate-500 text-xs">
                    {formatBytes(doc.file_size)}
                  </td>
                  <td className="px-6 py-3.5">
                    {doc.is_seed ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                        Seed Paper
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        Uploaded
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-3.5">
                    {doc.status === 'COMPLETED' && (
                      <span className="inline-flex items-center space-x-1 text-xs text-emerald-700 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Indexed</span>
                      </span>
                    )}
                    {doc.status === 'FAILED' && (
                      <span
                        className="inline-flex items-center space-x-1 text-xs text-rose-700 font-medium"
                        title={doc.error || 'Indexing error'}
                      >
                        <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
                        <span>Failed</span>
                      </span>
                    )}
                    {doc.status !== 'COMPLETED' && doc.status !== 'FAILED' && (
                      <div className="flex items-center space-x-2">
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                        <span className="text-xs text-indigo-600 font-medium">
                          {doc.status} ({doc.progress || 0}%)
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-3.5 text-right">
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="text-slate-400 hover:text-rose-600 p-1"
                      title="Delete document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

