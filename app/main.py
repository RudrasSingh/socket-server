# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import math

app = FastAPI()

# -------------------------
# 🔒 Restricted Area Logic
# -------------------------
RESTRICTED_CENTER = (28.6129, 77.2295)  # India Gate, Delhi
RESTRICTED_RADIUS_KM = 1.0


def is_in_restricted_area(lat: float, lon: float) -> bool:
    """Check if location is inside restricted area (circle)"""
    R = 6371
    dlat = math.radians(RESTRICTED_CENTER[0] - lat)
    dlon = math.radians(RESTRICTED_CENTER[1] - lon)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat))
        * math.cos(math.radians(RESTRICTED_CENTER[0]))
        * math.sin(dlon / 2) ** 2
    )
    distance = R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    return distance <= RESTRICTED_RADIUS_KM


# -------------------------
# 📡 WebSocket Handler
# -------------------------
@app.websocket("/ws/location")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔗 Client connected")
    
    try:
        # Wait for messages and maintain connection
        while True:
            data = await websocket.receive_json()
            
            # Only respond to location messages
            if data.get("type") == "location":
                lat = data.get("latitude")
                lon = data.get("longitude")

                print(f"📍 Received location: {lat}, {lon}")

                # Prepare response
                response = {
                    "type": "location_ack",
                    "status": "ok", 
                    "lat": lat, 
                    "lon": lon
                }

                # Restricted area check
                if is_in_restricted_area(lat, lon):
                    response["restricted"] = True
                    response["message"] = "⚠️ Entered restricted area!"
                else:
                    response["restricted"] = False
                    response["message"] = "✅ Location received"

                await websocket.send_json(response)
            else:
                # For all other message types, respond with location not received
                response = {
                    "type": "error",
                    "message": "Location not received!"
                }
                await websocket.send_json(response)

    except WebSocketDisconnect:
        print("❌ Client disconnected")
