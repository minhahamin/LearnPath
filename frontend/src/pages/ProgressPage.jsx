import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getRoadmap, getRoadmapSteps } from "../api/client.js";
import Timeline from "../components/Timeline.jsx";

const TERMINAL_STATUSES = new Set(["success", "partial", "failed"]);

function describeLatestStep(step) {
  if (!step) return "검색 계획을 세우는 중...";

  if (step.step_type === "action") {
    const match = step.content.match(/query=['"](.+?)['"]/);
    return match ? `'${match[1]}' 검색 중...` : "웹을 검색하는 중...";
  }
  if (step.step_type === "observation") {
    return "자료를 평가하는 중...";
  }
  const retryMatch = step.content.match(/최종 로드맵 생성 시도 (\d+)\/(\d+)/);
  if (retryMatch) {
    const [, attempt, total] = retryMatch;
    return attempt === "1"
      ? "수집한 자료로 로드맵을 만드는 중..."
      : `일부 자료의 근거가 부족해 다시 확인하는 중... (재시도 ${attempt - 1}/${total - 1})`;
  }
  return "검색 계획을 세우는 중...";
}

export default function ProgressPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const roadmapQuery = useQuery({
    queryKey: ["roadmap", id],
    queryFn: () => getRoadmap(id),
    refetchInterval: (query) => (TERMINAL_STATUSES.has(query.state.data?.status) ? false : 1500),
  });

  const stepsQuery = useQuery({
    queryKey: ["roadmap-steps", id],
    queryFn: () => getRoadmapSteps(id),
    refetchInterval: () => (TERMINAL_STATUSES.has(roadmapQuery.data?.status) ? false : 1500),
  });

  const status = roadmapQuery.data?.status;

  useEffect(() => {
    if (status === "success" || status === "partial") {
      navigate(`/roadmaps/${id}`, { replace: true });
    }
  }, [status, id, navigate]);

  const steps = stepsQuery.data || [];
  const latestStep = steps[steps.length - 1];

  return (
    <div>
      <div className="hero" style={{ padding: "8px 0 8px" }}>
        <h1 style={{ fontSize: "1.4rem" }}>{roadmapQuery.data?.topic || "큐레이션 진행 중"}</h1>
      </div>

      {status === "failed" ? (
        <>
          <div className="status-banner" style={{ color: "var(--danger)" }}>
            큐레이션에 실패했습니다.
          </div>
          <button className="btn-primary" onClick={() => navigate("/")}>
            다시 시도
          </button>
        </>
      ) : (
        <div className="status-banner">
          <span className="spinner" />
          {describeLatestStep(latestStep)}
        </div>
      )}

      {steps.length > 0 && <Timeline steps={steps} />}
    </div>
  );
}
