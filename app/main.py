# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import math
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# -------------------------
# 🔒 Restricted Area Logic
# -------------------------
RESTRICTED_CENTER = (22.881658, 88.398118)  # Kolkata sector 5
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
    logger.info("🔗 Client connected")
    
    try:
        # Wait for messages and maintain connection
        while True:
            try:
                # Try to receive and parse JSON
                data = await websocket.receive_json()
                
                # Check if location data is present (latitude and longitude)
                lat_raw = data.get("latitude")
                lon_raw = data.get("longitude")
                
                if lat_raw is not None and lon_raw is not None:
                    try:
                        # Convert to float (handles both string and number inputs)
                        lat = float(lat_raw)
                        lon = float(lon_raw)
                        
                        logger.info(f"📍 Received location: {lat}, {lon}")

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
                    except (ValueError, TypeError):
                        # Invalid latitude/longitude values
                        logger.warning("⚠️ Invalid latitude/longitude values")
                        response = {
                            "type": "error",
                            "message": "Location not received!"
                        }
                        await websocket.send_json(response)
                else:
                    # No location data found
                    logger.warning("⚠️ No location data found in message")
                    response = {
                        "type": "error",
                        "message": "Location not received!"
                    }
                    await websocket.send_json(response)
                    
            except WebSocketDisconnect:
                # Client disconnected, break out of the loop
                logger.info("❌ Client disconnected")
                break
            except json.JSONDecodeError:
                # Handle invalid JSON
                logger.warning("⚠️ Invalid JSON received")
                try:
                    response = {
                        "type": "error",
                        "message": "Location not received!"
                    }
                    await websocket.send_json(response)
                except:
                    # If we can't send, connection is probably closed
                    break
            except Exception as e:
                # Handle other parsing errors
                logger.error(f"⚠️ Error parsing message: {e}")
                try:
                    response = {
                        "type": "error",
                        "message": "Location not received!"
                    }
                    await websocket.send_json(response)
                except:
                    # If we can't send, connection is probably closed
                    break

    except WebSocketDisconnect:
        logger.info("❌ Client disconnected")
