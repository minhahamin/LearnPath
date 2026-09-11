import { useState } from "react";

const LABELS = { thought: "Thought", action: "Action", observation: "Observation" };
const LEVEL_LABELS = { beginner: "입문", intermediate: "중급", advanced: "고급" };
const CONFIDENCE_ICON = { high: "⭐", medium: "🌙", low: "☁️" };

function ObservationDetail({ evaluations }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="observation-detail">
      <button type="button" className="observation-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? "▲ 검색 결과 접기" : `▼ 검색 결과 ${evaluations.length}건 자세히 보기`}
      </button>
      {open && (
        <div className="observation-list">
          {evaluations.map((item, i) => (
            <div key={i} className={`observation-item${item.relevant ? "" : " not-relevant"}`}>
              <div className="observation-item-top">
                <a href={item.url} target="_blank" rel="noreferrer">
                  {item.title || item.url}
                </a>
                {item.relevant ? (
                  <span className="observation-tag">
                    {CONFIDENCE_ICON[item.confidence] || ""} {LEVEL_LABELS[item.level] || item.level}
                  </span>
                ) : (
                  <span className="observation-tag skip">제외됨</span>
                )}
              </div>
              {item.snippet && <p className="observation-snippet">{item.snippet}</p>}
              {item.reason && <p className="observation-reason">💬 {item.reason}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Timeline({ steps }) {
  return (
    <div className="timeline">
      {steps.map((step) => (
        <div key={step.step_order} className={`timeline-step ${step.step_type}`}>
          <span className="step-label">{LABELS[step.step_type] || step.step_type}</span>
          <div>{step.content}</div>
          {step.data?.evaluations && <ObservationDetail evaluations={step.data.evaluations} />}
        </div>
      ))}
    </div>
  );
}
