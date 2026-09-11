import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listRoadmaps } from "../api/client.js";

const STATUS_LABELS = { success: "🎀 완료", partial: "🌤️ 부분 완료", failed: "💧 실패", running: "🌀 진행 중" };

export default function HistoryPage() {
  const { data: roadmaps, isLoading } = useQuery({
    queryKey: ["roadmaps"],
    queryFn: listRoadmaps,
  });

  if (isLoading) return null;

  if (!roadmaps || roadmaps.length === 0) {
    return <div className="empty-state">아직 생성된 로드맵이 없습니다.</div>;
  }

  return (
    <div className="history-list">
      {roadmaps.map((r) => (
        <Link key={r.id} to={r.status === "running" ? `/roadmaps/${r.id}/progress` : `/roadmaps/${r.id}`} className="history-item">
          <div>
            <div className="topic">{r.topic}</div>
            <div className="date">{new Date(r.created_at).toLocaleString("ko-KR")}</div>
          </div>
          <span className={`status-pill ${r.status}`}>{STATUS_LABELS[r.status] || r.status}</span>
        </Link>
      ))}
    </div>
  );
}
