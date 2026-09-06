from sqlalchemy import Column, Integer, Float, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class MP(Base):
    __tablename__ = "mps"
    mp_id = Column(String(50), primary_key=True, index=True)
    mp_name = Column(String(200), nullable=False, index=True)
    house = Column(String(50))
    state = Column(String(100), index=True)
    constituency = Column(String(200), index=True)
    allocated_amount = Column(Float)

    projects = relationship("Project", back_populates="mp")

class Project(Base):
    __tablename__ = "projects"
    project_id = Column(String(100), primary_key=True, index=True)
    mp_id = Column(String(50), ForeignKey("mps.mp_id"), index=True)
    house = Column(String(50))
    state = Column(String(100), index=True)
    mp_name = Column(String(200))
    constituency = Column(String(200))
    work_category = Column(String(200), index=True)
    work_raw = Column(Text)
    work_description = Column(Text)
    recommended_date = Column(String(30))
    sanction_date = Column(String(30))
    sanction_amount = Column(Float)
    status = Column(String(100), index=True)
    recommended_amount = Column(Float)
    completion_date = Column(String(30))
    completed_amount = Column(Float)
    total_expenditure = Column(Float)
    first_expenditure_date = Column(String(30))
    last_expenditure_date = Column(String(30))
    payment_count = Column(Integer)
    vendor_count = Column(Integer)
    is_completed = Column(Integer)
    utilization_ratio = Column(Float)
    recommendation_to_sanction_days = Column(Float)
    sanction_to_completion_days = Column(Float)
    sanction_to_last_expenditure_days = Column(Float)
    progress_pct = Column(Float)
    delay_days = Column(Integer)
    is_delayed = Column(Integer)
    expected_completion_date = Column(String(30))

    mp = relationship("MP", back_populates="projects")

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    project_id = Column(String(100), ForeignKey("projects.project_id"), primary_key=True)
    cost_anomaly_score = Column(Float)
    cost_risk_level = Column(String(30))
    overspend_flag = Column(Integer)
    cost_reasons = Column(Text)
    delay_anomaly_score = Column(Float)
    duplicate_risk_score = Column(Float)
    duplicate_match_count = Column(Integer)
    duplicate_high_count = Column(Integer)
    duplicate_medium_count = Column(Integer)
    duplicate_low_count = Column(Integer)
    duplicate_max_similarity = Column(Float)
    strongest_duplicate_match = Column(String(100))
    duplicate_reason = Column(Text)
    overall_risk_score = Column(Float)
    risk_level = Column(String(30), index=True)
    risk_reasons = Column(Text)
    assessment_date = Column(String(30))

class RiskHistory(Base):
    __tablename__ = "risk_history"
    id = Column(Integer, primary_key=True)
    project_id = Column(String(100), ForeignKey("projects.project_id"), index=True)
    assessment_date = Column(String(30), index=True)
    cost_score = Column(Float)
    delay_score = Column(Float)
    duplicate_score = Column(Float)
    overall_score = Column(Float)
    risk_level = Column(String(30))
    risk_reasons = Column(Text)

class DuplicateAlert(Base):
    __tablename__ = "duplicate_alerts"
    id = Column(Integer, primary_key=True)
    project_id = Column(String(100), ForeignKey("projects.project_id"), index=True)
    matched_project_id = Column(String(100), ForeignKey("projects.project_id"), index=True)
    similarity = Column(Float)
    alert_score = Column(Float)
    alert_level = Column(String(30))
    same_mp = Column(Integer)
    same_constituency = Column(Integer)
    similar_amount = Column(Integer)
    reason = Column(Text)


class LivePrediction(Base):
    __tablename__ = "live_predictions"
    id = Column(Integer, primary_key=True)
    project_id = Column(String(100), index=True)
    predicted_at = Column(String(40), index=True)
    risk_score = Column(Float)
    risk_level = Column(String(30))
    cost_anomaly_score = Column(Float)
    delay_risk_score = Column(Float)
    duplicate_similarity_score = Column(Float)
    risk_reasons = Column(Text)
    input_payload = Column(Text)
    was_update = Column(Integer, default=0)
