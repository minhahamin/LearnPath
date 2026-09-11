import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { curate } from "../api/client.js";

export default function InputPage() {
  const [topic, setTopic] = useState("");
  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: curate,
    onSuccess: (data) => {
      navigate(`/roadmaps/${data.roadmap_id}/progress`);
    },
  });

  function handleSubmit(e) {
    e.preventDefault();
    if (!topic.trim()) return;
    mutation.mutate(topic.trim());
  }

  return (
    <div>
      <div className="hero">
        <h1>무엇을 배우고 싶으신가요?</h1>
        <p>
          관심 있는 주제를 입력하면 에이전트가 ReAct(Thought → Action → Observation) 루프로 웹을 검색·평가해
          난이도별 학습 로드맵을 만들어드립니다.
        </p>
      </div>

      <form className="curate-form" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="예: React Hooks, 도커 컨테이너, 회귀 분석..."
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          disabled={mutation.isPending}
          autoFocus
        />
        <button type="submit" className="btn-primary" disabled={mutation.isPending || !topic.trim()}>
          {mutation.isPending ? "시작하는 중..." : "큐레이션 시작"}
        </button>
      </form>

      {mutation.isError && (
        <div className="error-banner">
          요청에 실패했습니다: {mutation.error?.response?.data?.detail || mutation.error?.message}
        </div>
      )}
    </div>
  );
}
