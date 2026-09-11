const LABELS = { thought: "Thought", action: "Action", observation: "Observation" };

export default function Timeline({ steps }) {
  return (
    <div className="timeline">
      {steps.map((step) => (
        <div key={step.step_order} className={`timeline-step ${step.step_type}`}>
          <span className="step-label">{LABELS[step.step_type] || step.step_type}</span>
          <div>{step.content}</div>
        </div>
      ))}
    </div>
  );
}
