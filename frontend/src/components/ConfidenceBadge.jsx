const LABELS = { high: "⭐ 신뢰도 높음", medium: "🌙 신뢰도 보통", low: "☁️ 신뢰도 낮음" };

export default function ConfidenceBadge({ confidence }) {
  const level = confidence in LABELS ? confidence : "low";
  return <span className={`confidence-badge ${level}`}>{LABELS[level]}</span>;
}
