from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import RedirectResponse
from typing import List, Dict, Any
from api.schemas import NetworkFlow, TrafficPrediction, DecisionResponse
from core.engine import DecisionManager
from ml.predictor import TrafficPredictor
from models.enums import IncidentStatus

app = FastAPI(title="Smart SOC Decision Engine", version="2.0.0")

decision_manager = DecisionManager()
predictor = TrafficPredictor()

# In-memory DB for incidents
INCIDENTS_DB: Dict[str, DecisionResponse] = {}

@app.get("/", include_in_schema=False)
async def root():
    """Redirects root URL to the interactive API documentation."""
    return RedirectResponse(url="/docs")

@app.post("/api/v1/decision/analyze", response_model=DecisionResponse)
async def analyze_traffic(flow: NetworkFlow):
    """
    Ingests raw network flow data, runs ML inference, and computes the SOC decision.
    """
    # 1. ML Inference
    attack_type, confidence = predictor.predict(
        src_port=flow.src_port,
        dest_port=flow.dest_port,
        protocol_str=flow.protocol,
        packet_count=flow.packet_count,
        flow_duration=flow.flow_duration
    )
    
    prediction = TrafficPrediction(
        attack_type=attack_type,
        confidence=confidence,
        flow_context=flow
    )
    
    # 2. Decision Engine Processing
    decision = decision_manager.process(prediction)
    
    # 3. Store Incident
    INCIDENTS_DB[decision.incident_id] = decision
    
    # 4. Print Real-Time Analysis to Terminal
    print("\n" + "="*60)
    print(f"🚨 INCOMING TRAFFIC: {flow.src_ip}:{flow.src_port} -> {flow.dest_ip}:{flow.dest_port} ({flow.protocol})")
    print(f"🧠 ML PREDICTION:   {decision.attack_type} (Confidence: {decision.confidence:.2f}%)")
    print(f"⚠️ RISK SCORE:      {decision.risk_score:.1f} | Severity: {decision.severity}")
    print(f"🤖 AUTO LEVEL:      {decision.automation_level} | Playbook: {decision.playbook}")
    print(f"🛠️ ACTION TAKEN:    {decision.recommended_action}")
    print("="*60 + "\n")
    
    return decision

@app.get("/api/v1/decision/incidents", response_model=List[DecisionResponse])
async def get_incidents():
    """Returns all logged incidents."""
    return list(INCIDENTS_DB.values())

@app.post("/api/v1/decision/approve")
async def approve_incident(incident_id: str = Body(..., embed=True)):
    """Approves an incident that requires manual intervention (Level 2/3)."""
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    incident = INCIDENTS_DB[incident_id]
    if incident.incident_status != IncidentStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Incident is not pending approval")
        
    # Simulate execution and update
    incident.incident_status = IncidentStatus.MANUAL_MITIGATED
    incident.recommended_action = "Manual Approval Granted. Playbook Executed."
    INCIDENTS_DB[incident_id] = incident
    
    return {"status": "success", "message": f"Incident {incident_id} mitigated manually."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
