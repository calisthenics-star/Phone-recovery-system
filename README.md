# 📱 Phone Recovery System

A privacy-focused phone recovery platform designed to help users manage registered devices and track their last reported location.

## 🚀 Features

- 🔐 Owner authentication using Recovery ID and password
- 📱 Device registration and authentication
- 📊 Dashboard for managing registered devices
- 📍 Last reported device location on an interactive map
- 🕒 Location history interface
- 🚨 Lost-device status management
- 🔒 Secure password hashing and device credential storage

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Mobile Agent:** Android (Java)
- **Map:** Leaflet.js, OpenStreetMap

## 📂 Project Structure

- `backend/` — API and database
- `frontend/` — Web dashboard
- `android-agent/` — Android device agent

## ⚙️ Project Status

The project is under active development. Some features, including device reactivation and reliable location reporting, still require implementation and testing.

## 🔐 Security

- Passwords are hashed before storage.
- Device credentials are stored as hashes on the backend.
- Only authorized device owners should access their registered devices.

## 🎯 Goal

To build a secure and privacy-conscious platform that helps users recover and manage their lost devices.

---
**Developed by Manish Kumar Singh**
