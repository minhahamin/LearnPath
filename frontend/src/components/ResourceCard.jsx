import ConfidenceBadge from "./ConfidenceBadge.jsx";

export default function ResourceCard({ resource }) {
  return (
    <div className="resource-card">
      <div className="resource-card-top">
        <a href={resource.url} target="_blank" rel="noreferrer">
          {resource.title}
        </a>
        <ConfidenceBadge confidence={resource.confidence} />
      </div>
      <p className="reason">{resource.reason}</p>
    </div>
  );
}
