import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getRoadmap } from "../api/client.js";
import ResourceCard from "../components/ResourceCard.jsx";

const LEVEL_LABELS = { beginner: "🐣 입문", intermediate: "🌟 중급", advanced: "🚀 고급" };
const STATUS_LABELS = { success: "🎀 완료", partial: "🌤️ 부분 완료", failed: "💧 실패", running: "🌀 진행 중" };

export default function ResultPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: roadmap, isLoading } = useQuery({
    queryKey: ["roadmap", id],
    queryFn: () => getRoadmap(id),
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

      {(result?.levels || []).map((block) => (
        <section key={block.level} className="level-section">
          <h2>
            {LEVEL_LABELS[block.level] || block.level}
            <span className="level-badge">{block.resources.length}개 자료</span>
          </h2>
          <div className="resource-grid">
            {block.resources.map((resource, i) => (
              <ResourceCard key={i} resource={resource} />
            ))}
          </div>
        </section>
      ))}

      {(!result?.levels || result.levels.length === 0) && (
        <div className="empty-state">확인된 자료가 없습니다.</div>
      )}
    </div>
  );
}
