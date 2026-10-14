package com.phonerecovery.agent.network;

public final class ApiConfig {

    private ApiConfig() {
        // Prevent instantiation
    }

    // Development server
    public static final String BASE_URL = "http://10.0.2.15:8000";

    public static final String AUTHENTICATE_ENDPOINT =
            "/devices/authenticate";

    public static final String LOCATION_ENDPOINT =
            "/devices/location";

    public static final String LOST_MODE_ENDPOINT =
            "/devices/lost-mode";
}
