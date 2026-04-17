import { useRef, useState } from 'react';
import { Paperclip, X, FileText, Image, File } from 'lucide-react';
import { UploadedFile } from '../types';

interface FileUploadProps {
  onFilesChange: (files: UploadedFile[]) => void;
  onUpload: (file: File) => Promise<UploadedFile>;
}

function getFileIcon(type: string) {
  if (type.startsWith('image/')) return <Image size={14} />;
  if (type === 'application/pdf' || type.includes('text')) return <FileText size={14} />;
  return <File size={14} />;
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileUpload({ onFilesChange, onUpload }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);

  const handleSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    if (selected.length === 0) return;

    setUploading(true);
    try {
      const uploaded: UploadedFile[] = [];
      for (const file of selected) {
        try {
          const result = await onUpload(file);
          uploaded.push(result);
        } catch {
          uploaded.push({ name: file.name, size: file.size, type: file.type });
        }
      }
      const updated = [...files, ...uploaded];
      setFiles(updated);
      onFilesChange(updated);
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const removeFile = (index: number) => {
    const updated = files.filter((_, i) => i !== index);
    setFiles(updated);
    onFilesChange(updated);
  };

  return (
    <div className="flex flex-col gap-2">
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 px-1 pb-2">
          {files.map((file, i) => (
            <div
              key={i}
              className="flex items-center gap-1.5 bg-paper-100 border border-paper-200 rounded-lg px-2.5 py-1.5 text-xs text-paper-800 group"
            >
              <span className="text-paper-400">{getFileIcon(file.type)}</span>
              <span className="max-w-[120px] truncate font-medium">{file.name}</span>
              <span className="text-paper-300">{formatSize(file.size)}</span>
              <button
                onClick={() => removeFile(i)}
                className="ml-0.5 text-paper-300 hover:text-red-500 transition-colors"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
        onChange={handleSelect}
        className="hidden"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={uploading}
        className="flex items-center justify-center w-9 h-9 rounded-lg text-paper-700 hover:text-paper-900 hover:bg-paper-100 transition-all duration-300 disabled:opacity-50"
        title="Attach file"
      >
        <Paperclip size={18} className={uploading ? 'animate-pulse' : ''} />
      </button>
    </div>
  );
}
