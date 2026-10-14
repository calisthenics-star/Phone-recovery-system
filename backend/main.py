from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta 
import hashlib
import secrets
import uuid 

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from database import get_connection, init_database


app = FastAPI(title="Phone Recovery Backend")

app.add_middleware(
    CORSMiddleware,
allow_origins=[
    "http://10.0.2.15:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DeviceRegistration(BaseModel):
    device_name: str
    device_model: str

class OwnerRegistration(BaseModel):
    password: str

class OwnerLogin(BaseModel):
    recovery_id: str
    password: str

@app.post("/owners/register")
def register_owner(owner: OwnerRegistration):
    created_at = datetime.now(timezone.utc).isoformat()

    owner_id = str(uuid.uuid4())

    recovery_id = (
        "PR-"
        + secrets.token_hex(2).upper()
        + "-"
        + secrets.token_hex(2).upper()
    )

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        owner.password.encode(),
        salt,
        200000,
    ).hex()

    stored_password_hash = (
        salt.hex() + ":" + password_hash
    )

    connection = get_connection()

    try:
        connection.execute(
            """
            INSERT INTO owners
            (owner_id, recovery_id, password_hash, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                owner_id,
                recovery_id,
                stored_password_hash,
                created_at,
            ),
        )

        connection.commit()

    except Exception:
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Could not create owner account",
        )

    connection.close()

    return {
        "message": "Owner registered successfully",
        "recovery_id": recovery_id,
        "password_reminder": "Keep your recovery ID and password safe",
        "created_at": created_at,
    }

@app.post("/owners/login")
def login_owner(login: OwnerLogin):
    connection = get_connection()

    owner = connection.execute(
        """
        SELECT owner_id, password_hash
        FROM owners
        WHERE recovery_id = ?
        """,
        (login.recovery_id,),
    ).fetchone()

    if owner is None:
        connection.close()
        raise HTTPException(
            status_code=401,
            detail="Invalid recovery ID or password",
        )

    stored_password = owner["password_hash"]
    salt_hex, stored_hash = stored_password.split(":", 1)

    salt = bytes.fromhex(salt_hex)

    calculated_hash = hashlib.pbkdf2_hmac(
        "sha256",
        login.password.encode(),
        salt,
        200000,
    ).hex()

    if not secrets.compare_digest(calculated_hash, stored_hash):
        connection.close()
        raise HTTPException(
            status_code=401,
            detail="Invalid recovery ID or password",
        )

    session_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(
        session_token.encode()
    ).hexdigest()

    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(hours=24)

    connection.execute(
        """
        INSERT INTO owner_sessions
        (owner_id, token_hash, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            owner["owner_id"],
            token_hash,
            created_at.isoformat(),
            expires_at.isoformat(),
        ),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Owner login successful",
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
    }

def get_authenticated_owner(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    session_token = authorization[7:].strip()

    if not session_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    token_hash = hashlib.sha256(
        session_token.encode()
    ).hexdigest()

    connection = get_connection()

    session = connection.execute(
        """
        SELECT owner_id
        FROM owner_sessions
        WHERE token_hash = ?
        AND expires_at > ?
        """,
        (
            token_hash,
            datetime.now(timezone.utc).isoformat(),
        ),
    ).fetchone()

    connection.close()

    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )

    return session["owner_id"]


@app.get("/owners/me/devices")
def get_my_devices(
    authorization: str | None = Header(default=None)
):
    owner_id = get_authenticated_owner(authorization)

    connection = get_connection()

    devices = connection.execute(
        """
        SELECT
            device_id,
            device_name,
            device_model,
            status,
            registered_at,
            last_seen
        FROM devices
        WHERE owner_id = ?
        ORDER BY device_id
        """,
        (owner_id,),
    ).fetchall()

    connection.close()

    return {
        "owner_id": owner_id,
        "devices": [dict(device) for device in devices],
    }

init_database()


@app.get("/")
def home():
    return {"message": "Phone Recovery Backend is running"}


@app.post("/devices/register")
def register_device(
    device: DeviceRegistration,
    authorization: str | None = Header(default=None),
):
    owner_id = get_authenticated_owner(authorization)

    registered_at = datetime.now(timezone.utc).isoformat()

    # Generate a strong random credential for the device
    device_credential = secrets.token_urlsafe(32)

    # Store only the hash, never the actual credential
    credential_hash = hashlib.sha256(
        device_credential.encode()
    ).hexdigest()

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO devices
        (owner_id, device_name, device_model, registered_at, credential_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            owner_id,
            device.device_name,
            device.device_model,
            registered_at,
            credential_hash,
        ),
    )

    connection.commit()

    device_id = cursor.lastrowid

    connection.close()

    return {
        "message": "Device registered successfully",
        "device_id": device_id,
        "device_credential": device_credential,
        "device": {
            "device_name": device.device_name,
            "device_model": device.device_model,
            "owner_id": owner_id,
            "registered_at": registered_at,
            "status": "active",
        },
    }

@app.get("/devices/{device_id}")
def get_device(
    device_id: int,
    authorization: str | None = Header(default=None),
):
    owner_id = get_authenticated_owner(authorization)

    connection = get_connection()

    device = connection.execute(
        """
        SELECT
            device_id,
            owner_id,
            device_name,
            device_model,
            status,
            registered_at,
            last_seen
        FROM devices
        WHERE device_id = ?
        AND owner_id = ?
        """,
        (device_id, owner_id),
    ).fetchone()

    if device is None:
        connection.close()
        return {"message": "Device not found"}

    latest_location = connection.execute(
        """
        SELECT
            latitude,
            longitude,
            accuracy,
            reported_at
        FROM device_locations
        WHERE device_id = ?
        ORDER BY location_id DESC
        LIMIT 1
        """,
        (device_id,),
    ).fetchone()

    connection.close()

    response = dict(device)

    if latest_location is None:
        response["latest_location"] = None
    else:
        response["latest_location"] = dict(latest_location)

    return response

class DeviceAuthentication(BaseModel):
    device_id: int
    device_credential: str


class LocationReport(BaseModel):
    device_id: int
    device_credential: str
    latitude: float
    longitude: float
    accuracy: float | None = None

class LocationHistoryRequest(BaseModel):
    device_id: int

@app.post("/devices/authenticate")
def authenticate_device(auth: DeviceAuthentication):
    credential_hash = hashlib.sha256(
        auth.device_credential.encode()
    ).hexdigest()

    connection = get_connection()

    device = connection.execute(
        """
        SELECT device_id, owner_id, status
        FROM devices
        WHERE device_id = ? AND credential_hash = ?
        """,
        (auth.device_id, credential_hash),
    ).fetchone()

    connection.close()

    if device is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid device credentials",
        )

    return {
        "authenticated": True,
        "message": "Device authenticated successfully",
        "device_id": device["device_id"],
        "status": device["status"],
    }

@app.post("/devices/location")
def report_location(location: LocationReport):
    credential_hash = hashlib.sha256(
        location.device_credential.encode()
    ).hexdigest()

    connection = get_connection()

    device = connection.execute(
        """
        SELECT device_id, status
        FROM devices
        WHERE device_id = ?
        AND credential_hash = ?
        """,
        (location.device_id, credential_hash),
    ).fetchone()

    if device is None:
        connection.close()
        raise HTTPException(
            status_code=401,
            detail="Invalid device credentials",
        )

    reported_at = datetime.now(timezone.utc).isoformat()

    cursor = connection.execute(
        """
        INSERT INTO device_locations
        (device_id, latitude, longitude, accuracy, reported_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            location.device_id,
            location.latitude,
            location.longitude,
            location.accuracy,
            reported_at,
        ),
    )

    connection.execute(
        """
        UPDATE devices
        SET last_seen = ?
        WHERE device_id = ?
        """,
        (reported_at, location.device_id),
    )

    connection.commit()

    location_id = cursor.lastrowid

    connection.close()

    return {
        "message": "Location reported successfully",
        "location_id": location_id,
        "device_id": location.device_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracy": location.accuracy,
        "reported_at": reported_at,
    }


@app.post("/devices/locations/history")
def get_location_history(
    request: LocationHistoryRequest,
    authorization: str | None = Header(default=None),
):
    owner_id = get_authenticated_owner(authorization)

    connection = get_connection()

    device = connection.execute(
        """
        SELECT device_id, status
        FROM devices
        WHERE device_id = ?
        AND owner_id = ?
        """,
        (request.device_id, owner_id),
    ).fetchone()

    if device is None:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    locations = connection.execute(
        """
        SELECT
            location_id,
            device_id,
            latitude,
            longitude,
            accuracy,
            reported_at
        FROM device_locations
        WHERE device_id = ?
        ORDER BY reported_at DESC
        """,
        (request.device_id,),
    ).fetchall()

    connection.close()

    return {
        "device_id": request.device_id,
        "locations": [dict(location) for location in locations],
    }

class LostModeRequest(BaseModel):
    device_id: int


@app.post("/devices/lost-mode")
def enable_lost_mode(
    request: LostModeRequest,
    authorization: str | None = Header(default=None),
):
    owner_id = get_authenticated_owner(authorization)

    connection = get_connection()

    device = connection.execute(
        """
        SELECT device_id, owner_id, status
        FROM devices
        WHERE device_id = ?
        AND owner_id = ?
        """,
        (request.device_id, owner_id),
    ).fetchone()

    if device is None:
        connection.close()
        raise HTTPException(
            status_code=404,
            detail="Device not found",
        )

    connection.execute(
        """
        UPDATE devices
        SET status = 'lost'
        WHERE device_id = ?
        AND owner_id = ?
        """,
        (request.device_id, owner_id),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Lost mode enabled",
        "device_id": request.device_id,
        "status": "lost",
    }
