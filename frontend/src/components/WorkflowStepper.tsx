interface Step {
  id: string;
  label: string;
  description: string;
}

const WORKFLOW_STEPS: Step[] = [
  { id: "uploaded", label: "Upload", description: "PDF uploaded" },
  { id: "ocr_done", label: "OCR", description: "Text extracted" },
  { id: "reviewed", label: "Review", description: "Text reviewed" },
  { id: "parsed", label: "Parse", description: "Data parsed" },
  { id: "edited", label: "Edit", description: "Data edited" },
  { id: "ready_to_export", label: "Export", description: "Ready to export" },
];

interface WorkflowStepperProps {
  currentStage: string;
  compact?: boolean;
}

export default function WorkflowStepper({ currentStage, compact = false }: WorkflowStepperProps) {
  const currentIndex = WORKFLOW_STEPS.findIndex((step) => step.id === currentStage);

  return (
    <div style={{ padding: compact ? "0.5rem 0" : "1rem 0" }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "relative"
      }}>
        {/* Progress bar background */}
        <div
          style={{
            position: "absolute",
            top: compact ? "8px" : "12px",
            left: "0",
            right: "0",
            height: "2px",
            backgroundColor: "rgba(255, 255, 255, 0.1)",
            zIndex: 0,
          }}
        >
          {/* Progress bar fill */}
          <div
            style={{
              height: "100%",
              backgroundColor: "#4f9cff",
              width: `${(currentIndex / (WORKFLOW_STEPS.length - 1)) * 100}%`,
              transition: "width 0.3s ease",
            }}
          />
        </div>

        {/* Steps */}
        {WORKFLOW_STEPS.map((step, index) => {
          const isCompleted = index <= currentIndex;
          const isCurrent = index === currentIndex;

          return (
            <div
              key={step.id}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                flex: 1,
                position: "relative",
                zIndex: 1,
              }}
            >
              {/* Step circle */}
              <div
                style={{
                  width: compact ? "16px" : "24px",
                  height: compact ? "16px" : "24px",
                  borderRadius: "50%",
                  backgroundColor: isCompleted ? "#4f9cff" : "rgba(255, 255, 255, 0.1)",
                  border: isCurrent ? "3px solid #4f9cff" : "2px solid transparent",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "all 0.3s ease",
                  boxShadow: isCurrent ? "0 0 10px rgba(79, 156, 255, 0.5)" : "none",
                }}
              >
                {isCompleted && !isCurrent && (
                  <span style={{ color: "white", fontSize: compact ? "10px" : "12px" }}>✓</span>
                )}
              </div>

              {/* Step label */}
              {!compact && (
                <div
                  style={{
                    marginTop: "0.5rem",
                    textAlign: "center",
                    fontSize: "0.75rem",
                    color: isCompleted ? "#4f9cff" : "rgba(255, 255, 255, 0.5)",
                    fontWeight: isCurrent ? 600 : 400,
                  }}
                >
                  <div>{step.label}</div>
                  <div style={{ fontSize: "0.65rem", opacity: 0.7 }}>{step.description}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
