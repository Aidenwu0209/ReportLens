/**
 * F4 – PDF viewer + bbox highlighting overlay.
 *
 * Displays page images from the backend and overlays normalised bbox
 * highlights that correspond to evidence_refs.
 */

import { useEffect, useRef, useState } from 'react';
import apiClient from '../api/client';
import { useAppStore } from '../stores/appStore';
import type { EvidenceRef } from '../types/api';

interface PdfViewerProps {
  docId: string;
  versionId: string;
  pageCount: number;
}

export default function PdfViewer({ docId, versionId, pageCount }: PdfViewerProps) {
  const { activePage, activeHighlights, setHighlights } = useAppStore();
  const [currentPage, setCurrentPage] = useState(activePage);
  const [imageLoaded, setImageLoaded] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    setCurrentPage(activePage);
  }, [activePage]);

  useEffect(() => {
    setImageLoaded(false);
  }, [currentPage]);

  const imageUrl = apiClient.getPageImageUrl(docId, versionId, currentPage);

  // Filter highlights for current page
  const pageHighlights = activeHighlights.filter((h) => h.page_no === currentPage);

  return (
    <div className="flex flex-col h-full">
      {/* Page navigation */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
        <button
          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          disabled={currentPage <= 1}
          className="text-text-secondary hover:text-text-primary disabled:opacity-30 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <span className="text-text-secondary text-sm">
          {currentPage} / {pageCount}
        </span>
        <button
          onClick={() => setCurrentPage((p) => Math.min(pageCount, p + 1))}
          disabled={currentPage >= pageCount}
          className="text-text-secondary hover:text-text-primary disabled:opacity-30 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Image + overlays */}
      <div ref={containerRef} className="flex-1 overflow-auto relative bg-surface p-2">
        <div className="relative inline-block">
          {!imageLoaded && (
            <div className="w-full h-96 skeleton rounded-lg" />
          )}
          <img
            ref={imgRef}
            src={imageUrl}
            alt={`Page ${currentPage}`}
            className={`max-w-full rounded transition-opacity duration-300 ${
              imageLoaded ? 'opacity-100' : 'opacity-0 absolute'
            }`}
            onLoad={() => setImageLoaded(true)}
            crossOrigin="use-credentials"
          />

          {/* Bbox highlights */}
          {imageLoaded &&
            imgRef.current &&
            pageHighlights.map((h, idx) => {
              if (!h.bbox_norm || h.bbox_norm.length < 4) return null;
              const [x0, y0, x1, y1] = h.bbox_norm;
              const imgW = imgRef.current!.clientWidth;
              const imgH = imgRef.current!.clientHeight;
              return (
                <div
                  key={h.ref_id || idx}
                  className="bbox-highlight active"
                  style={{
                    left: `${x0 * imgW}px`,
                    top: `${y0 * imgH}px`,
                    width: `${(x1 - x0) * imgW}px`,
                    height: `${(y1 - y0) * imgH}px`,
                  }}
                  title={h.snippet || ''}
                />
              );
            })}
        </div>
      </div>
    </div>
  );
}
