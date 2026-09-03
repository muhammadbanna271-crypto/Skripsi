"""State pipeline (untuk UI + report): tahapan & STOP conditions."""

VALIDATION = "VALIDATION"
RELIABILITY = "RELIABILITY"
CFA = "CFA"
SEM = "SEM"
LCA = "LCA"
ML = "ML"
SHAP = "SHAP"
COMPLETED = "COMPLETED"
STOPPED = "STOPPED"


class PipelineState:
    """Lacak progres pipeline + status tiap tahap (untuk UI & report)."""

    def __init__(self):
        self.history = []  # list of {stage, status, message}
        self.status = "PENDING"

    def log(self, stage, status, message=None):
        self.history.append({"stage": stage, "status": status, "message": message})
        self.status = status

    def stop(self, stage, message):
        self.log(stage, STOPPED, message)

    def stages_summary(self):
        return [
            {"stage": h["stage"], "status": h["status"], "message": h["message"]}
            for h in self.history
        ]
