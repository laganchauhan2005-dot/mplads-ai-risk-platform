from app.database import SessionLocal
from app.models import MP, Project, RiskAssessment, RiskHistory, DuplicateAlert

db = SessionLocal()
try:
    print("MPLADS final database check")
    print("----------------------------")
    print("MPs:", db.query(MP).count())
    print("Projects:", db.query(Project).count())
    print("Risk assessments:", db.query(RiskAssessment).count())
    print("Risk history records:", db.query(RiskHistory).count())
    print("Duplicate alerts:", db.query(DuplicateAlert).count())
    print("High/Critical:", db.query(RiskAssessment).filter(RiskAssessment.risk_level.in_(["HIGH", "CRITICAL"])).count())
finally:
    db.close()
