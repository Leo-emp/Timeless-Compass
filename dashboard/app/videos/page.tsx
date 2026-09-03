"use client";

import { useEffect, useState } from "react";
import { listVideos, deleteVideo, uploadToYoutube, formatDuration, formatDate } from "@/lib/api";
import type { Video } from "@/lib/api";

// ============================================================
// VIDEOS PAGE — Library of all generated videos
// ============================================================

export default function VideosPage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadVideos();
  }, []);

  async function loadVideos() {
    try {
      const data = await listVideos();
      setVideos(data);
    } catch {
      // --- API might be offline ---
    }
    setLoading(false);
  }

  async function handleUpload(videoId: string) {
    try {
      await uploadToYoutube(videoId);
      // --- Poll for upload completion ---
      setTimeout(loadVideos, 3000);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Upload failed");
    }
  }

  async function handleDelete(videoId: string) {
    if (!confirm("Delete this video record? The file will be kept on disk.")) return;
    try {
      await deleteVideo(videoId);
      setVideos(videos.filter((v) => v.id !== videoId));
    } catch {
      // --- Handle error ---
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p style={{ color: "var(--color-text-muted)" }}>Loading videos...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      {/* --- Page header --- */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold mb-1">Video Library</h1>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            {videos.length} video{videos.length !== 1 ? "s" : ""} generated
          </p>
        </div>
      </div>

      {videos.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-sm mb-2" style={{ color: "var(--color-text-muted)" }}>
            No videos generated yet
          </p>
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
            Go to Generate to create your first documentary
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {videos.map((video) => (
            <div key={video.id} className="card">
              <div className="flex items-start justify-between">
                {/* --- Video info --- */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-bold mb-1 truncate">{video.title}</h3>
                  <p
                    className="text-sm mb-3 line-clamp-2"
                    style={{ color: "var(--color-text-secondary)" }}
                  >
                    {video.description}
                  </p>

                  {/* --- Metadata row --- */}
                  <div className="flex items-center gap-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
                    <span>{formatDuration(video.duration_seconds)}</span>
                    <span>{video.file_size_mb.toFixed(1)} MB</span>
                    <span>{video.format.toUpperCase()}</span>
                    <span>{video.quality}</span>
                    <span>{formatDate(video.created_at)}</span>
                  </div>

                  {/* --- Tags --- */}
                  {video.tags && video.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {video.tags.slice(0, 8).map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-0.5 rounded text-[11px]"
                          style={{
                            background: "var(--color-surface-2)",
                            color: "var(--color-text-muted)",
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* --- Actions --- */}
                <div className="flex flex-col gap-2 ml-6">
                  {/* --- YouTube status --- */}
                  {video.youtube_status === "uploaded" ? (
                    <a
                      href={video.youtube_url || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary text-xs"
                    >
                      View on YouTube
                    </a>
                  ) : video.youtube_status === "uploading" ? (
                    <span className="badge badge-warning">Uploading...</span>
                  ) : (
                    <button
                      onClick={() => handleUpload(video.id)}
                      className="btn btn-primary text-xs"
                    >
                      Upload to YouTube
                    </button>
                  )}

                  {/* --- Preview link --- */}
                  <a
                    href={`/api/videos/${video.id}/file`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary text-xs"
                  >
                    Preview
                  </a>

                  {/* --- Delete --- */}
                  <button
                    onClick={() => handleDelete(video.id)}
                    className="btn btn-danger text-xs"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
