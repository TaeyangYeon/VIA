import React, { useState, useRef, useCallback } from 'react';
import { Upload, X, Trash2, Image } from 'lucide-react';
import { useAppSelector, useAppDispatch } from '../../store/hooks';
import {
  selectAnalysisImages,
  selectTestImages,
  addImage,
  removeImage,
  clearImagesByPurpose,
  type ImageMeta,
} from '../../store/slices/imagesSlice';
import {
  uploadImage as apiUpload,
  deleteImage as apiDelete,
  clearImages as apiClear,
} from '../../services/api';
import type { ImageMeta as ApiImageMeta } from '../../services/types';
import {
  bg_secondary,
  bg_hover,
  border_default,
  text_primary,
  text_secondary,
  text_disabled,
  accent_success,
  accent_error,
} from '../../styles/design-tokens';

export function validateFilename(filename: string): boolean {
  return /^(OK|NG)_\d+\.(png|jpg|jpeg|bmp|tiff)$/i.test(filename);
}

function mapApiImage(img: ApiImageMeta): ImageMeta {
  return {
    id: img.image_id,
    filename: img.filename,
    purpose: img.purpose,
    label: img.label,
    uploaded_at: img.uploaded_at,
    path: img.path,
  };
}

type Purpose = 'analysis' | 'test';

interface ImageSectionProps {
  purpose: Purpose;
  label: string;
}

function ImageSection({ purpose, label }: ImageSectionProps) {
  const dispatch = useAppDispatch();
  const images = useAppSelector(purpose === 'analysis' ? selectAnalysisImages : selectTestImages);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewUrls, setPreviewUrls] = useState<Map<string, string>>(new Map());
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const fileArray = Array.from(files);
      for (const file of fileArray) {
        if (!validateFilename(file.name)) {
          setError(
            `Invalid filename: "${file.name}". Use OK_N or NG_N format (e.g. OK_1.png)`,
          );
          continue;
        }
        setError(null);
        setLoading(true);
        try {
          const blobUrl = URL.createObjectURL(file);
          const result = await apiUpload(file, purpose);
          const mapped = mapApiImage(result);
          setPreviewUrls((prev) => new Map(prev).set(mapped.id, blobUrl));
          dispatch(addImage(mapped));
        } catch (err) {
          const msg = err instanceof Error ? err.message : 'Upload failed';
          setError(msg);
        } finally {
          setLoading(false);
        }
      }
    },
    [purpose, dispatch],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles],
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
      e.target.value = '';
    }
  };

  const handleDelete = async (img: ImageMeta) => {
    try {
      await apiDelete(img.id);
      setPreviewUrls((prev) => {
        const next = new Map(prev);
        const url = next.get(img.id);
        if (url) URL.revokeObjectURL(url);
        next.delete(img.id);
        return next;
      });
      dispatch(removeImage({ id: img.id, purpose }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const handleClearAll = async () => {
    try {
      await apiClear(purpose);
      previewUrls.forEach((url) => URL.revokeObjectURL(url));
      setPreviewUrls(new Map());
      dispatch(clearImagesByPurpose(purpose));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Clear failed');
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold" style={{ color: text_primary }}>
            {label}
          </h2>
          <span
            className="text-xs font-mono px-1.5 py-0.5 rounded bg-white/5"
            style={{ color: text_secondary }}
            data-testid={`${purpose}-count`}
          >
            {images.length}
          </span>
        </div>
        {images.length > 0 && (
          <button
            data-testid={`${purpose}-clear-btn`}
            onClick={handleClearAll}
            className="flex items-center gap-1 text-xs transition-all duration-150 px-2 py-1 rounded hover:bg-white/5"
            style={{ color: text_secondary }}
          >
            <Trash2 size={11} />
            Clear All
          </button>
        )}
      </div>

      {/* Drop zone */}
      <div
        data-testid={`${purpose}-drop-zone`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className="relative rounded-lg border border-dashed transition-all duration-150 cursor-pointer"
        style={{
          borderColor: isDragging ? '#555' : border_default,
          backgroundColor: isDragging ? bg_hover : bg_secondary,
          minHeight: '80px',
        }}
        onClick={() => images.length === 0 && fileInputRef.current?.click()}
      >
        {images.length === 0 ? (
          <div className="flex flex-col items-center gap-1.5 py-5 px-4">
            <Upload size={18} style={{ color: text_disabled }} />
            <p className="text-xs text-center" style={{ color: text_disabled }}>
              Drop images here or click to upload
            </p>
            <p className="text-xs" style={{ color: text_disabled }}>
              PNG · JPG · BMP · TIFF
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-2 p-3">
            {images.map((img) => {
              const preview = previewUrls.get(img.id);
              return (
                <div
                  key={img.id}
                  className="relative group rounded overflow-hidden bg-white/5 border transition-all duration-150"
                  style={{ borderColor: border_default }}
                >
                  {preview ? (
                    <img
                      src={preview}
                      alt={img.filename}
                      className="w-full aspect-square object-cover"
                    />
                  ) : (
                    <div
                      className="w-full aspect-square flex items-center justify-center"
                      style={{ backgroundColor: bg_hover }}
                    >
                      <Image size={16} style={{ color: text_disabled }} />
                    </div>
                  )}
                  {/* OK/NG badge */}
                  <span
                    className="absolute top-1 left-1 text-xs font-bold px-1 py-0.5 rounded"
                    style={{
                      backgroundColor: img.label === 'OK' ? accent_success : accent_error,
                      color: '#000',
                      fontSize: '9px',
                    }}
                  >
                    {img.label}
                  </span>
                  {/* Delete button */}
                  <button
                    data-testid={`delete-${img.id}`}
                    aria-label={`Delete ${img.filename}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(img);
                    }}
                    className="absolute top-1 right-1 rounded p-0.5 transition-all duration-150 bg-black/70"
                  >
                    <X size={10} style={{ color: '#fff' }} />
                  </button>
                  {/* Filename */}
                  <div
                    className="px-1 py-0.5 truncate"
                    style={{ fontSize: '9px', color: text_secondary }}
                  >
                    {img.filename}
                  </div>
                </div>
              );
            })}
            {/* Add more tile */}
            <div
              className="flex items-center justify-center rounded border border-dashed transition-all duration-150 cursor-pointer aspect-square"
              style={{ borderColor: border_default }}
              onClick={(e) => {
                e.stopPropagation();
                fileInputRef.current?.click();
              }}
            >
              <Upload size={14} style={{ color: text_disabled }} />
            </div>
          </div>
        )}

        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-lg">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full bg-white/50 animate-pulse"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        data-testid={`${purpose}-file-input`}
        accept=".png,.jpg,.jpeg,.bmp,.tiff"
        multiple
        className="hidden"
        onChange={handleFileInput}
      />

      {/* Error message */}
      {error && (
        <p className="text-xs" style={{ color: accent_error }}>
          {error}
        </p>
      )}
    </div>
  );
}

export default function InputPanel() {
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="flex items-center gap-2 mb-6">
        <Image size={16} style={{ color: '#f5f5f5' }} />
        <h1 className="text-base font-semibold" style={{ color: '#f5f5f5' }}>
          Input Images
        </h1>
      </div>
      <div className="flex flex-col gap-8">
        <ImageSection purpose="analysis" label="Analysis Images" />
        <ImageSection purpose="test" label="Test Images" />
      </div>
    </div>
  );
}
