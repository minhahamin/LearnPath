import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getRoadmap, updateProgress } from "../api/client.js";
import ResourceCard from "../components/ResourceCard.jsx";

const LEVEL_LABELS = { beginner: "🐣 입문", intermediate: "🌟 중급", advanced: "🚀 고급" };
const STATUS_LABELS = { success: "🎀 완료", partial: "🌤️ 부분 완료", failed: "💧 실패", running: "🌀 진행 중" };

export default function ResultPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: roadmap, isLoading } = useQuery({
    queryKey: ["roadmap", id],
    queryFn: () => getRoadmap(id),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ url, completed }) => updateProgress(id, url, completed),
    onMutate: async ({ url, completed }) => {
      await queryClient.cancelQueries({ queryKey: ["roadmap", id] });
      const previous = queryClient.getQueryData(["roadmap", id]);
      queryClient.setQueryData(["roadmap", id], (old) =>
        old ? { ...old, progress: { ...old.progress, [url]: completed } } : old
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(["roadmap", id], context.previous);
    },
  });

  useEffect(() => {
    if (roadmap?.status === "running") {
      navigate(`/roadmaps/${id}/progress`, { replace: true });
    }
  }, [roadmap, id, navigate]);

  if (isLoading) return null;
  if (roadmap?.status === "running") return null;

  if (!roadmap || (roadmap.status === "failed" && !roadmap.result)) {
    return (
      <div className="empty-state">
        <p>로드맵을 불러올 수 없습니다.</p>
      </div>
    );
  }

  const result = roadmap.result;
  const progress = roadmap.progress || {};
  const allResources = (result?.levels || []).flatMap((block) => block.resources);
  const completedCount = allResources.filter((r) => progress[r.url]).length;
  const totalCount = allResources.length;
  const percent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div>
      <div className="result-header">
        <h1>{result?.topic || roadmap.topic}</h1>
        {result?.summary && <p>{result.summary}</p>}
        <div className="result-meta">
          <span className={`status-pill ${roadmap.status}`}>{STATUS_LABELS[roadmap.status]}</span>
          {result?.total_estimated_hours != null && <span>예상 학습 시간: {result.total_estimated_hours}시간</span>}
        </div>
      </div>

      {totalCount > 0 && (
        <div className="progress-tracker">
          <div className="progress-tracker-label">
            <span>📌 진행률</span>
            <span>
              {completedCount} / {totalCount} 완료
            </span>
          </div>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${percent}%` }} />
          </div>
        </div>
      )}

      {(result?.levels || []).map((block) => {
        const levelCompleted = block.resources.filter((r) => progress[r.url]).length;
        return (
          <section key={block.level} className="level-section">
            <h2>
              {LEVEL_LABELS[block.level] || block.level}
              <span className="level-badge">
                {levelCompleted}/{block.resources.length} 완료
              </span>
            </h2>
            <div className="resource-grid">
              {block.resources.map((resource, i) => (
                <ResourceCard
                  key={i}
                  resource={resource}
                  completed={!!progress[resource.url]}
                  onToggle={(completed) => toggleMutation.mutate({ url: resource.url, completed })}
                />
              ))}
            </div>
          </section>
        );
      })}

      {(!result?.levels || result.levels.length === 0) && (
        <div className="empty-state">확인된 자료가 없습니다.</div>
      )}
    </div>
  );
}
