from decision_engine.core.engine import DecisionManager

engine = DecisionManager()

# Test 1: Level 4 (Critical asset)
pred1 = {
    "attack_type": "DoS SYN Flood",
    "confidence": 98.5,
    "source_ip": "192.168.1.100",
    "destination_ip": "10.0.0.5",
    "packet_count": 150000
}
res1 = engine.process_prediction(pred1)
print("Test 1 Level:", res1["automation_level"])
assert res1["automation_level"] == "Level 4"

# Test 2: Level 5 (Non-critical asset)
pred2 = {
    "attack_type": "DoS SYN Flood",
    "confidence": 99.1,
    "source_ip": "203.0.113.5",
    "destination_ip": "10.0.0.10",
    "packet_count": 200000
}
res2 = engine.process_prediction(pred2)
print("Test 2 Level:", res2["automation_level"])
assert res2["automation_level"] == "Level 5"

# Test 3: Level 0 (Benign)
pred3 = {
    "attack_type": "Benign",
    "confidence": 95.0,
    "source_ip": "198.51.100.1",
    "destination_ip": "10.0.0.5",
    "packet_count": 50
}
res3 = engine.process_prediction(pred3)
print("Test 3 Level:", res3["automation_level"])
assert res3["automation_level"] == "Level 0"

print("All tests passed!")
