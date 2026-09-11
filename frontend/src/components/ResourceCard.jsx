import ConfidenceBadge from "./ConfidenceBadge.jsx";

export default function ResourceCard({ resource, completed, onToggle }) {
  return (
    <div className={`resource-card${completed ? " completed" : ""}`}>
      <label className="resource-check">
        <input type="checkbox" checked={!!completed} onChange={(e) => onToggle?.(e.target.checked)} />
      </label>
      <div className="resource-card-body">
        <div className="resource-card-top">
          <a href={resource.url} target="_blank" rel="noreferrer">
            {resource.title}
          </a>
          <ConfidenceBadge confidence={resource.confidence} />
        </div>
        <p className="reason">{resource.reason}</p>
      </div>
    </div>
  );
}
