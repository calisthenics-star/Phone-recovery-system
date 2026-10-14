package com.phonerecovery.agent.network;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class ApiClient {

    public static String authenticateDevice(
            int deviceId,
            String deviceCredential
    ) throws Exception {

        URL url = new URL(
                ApiConfig.BASE_URL + ApiConfig.AUTHENTICATE_ENDPOINT
        );

        HttpURLConnection connection =
                (HttpURLConnection) url.openConnection();

        connection.setRequestMethod("POST");
        connection.setRequestProperty(
                "Content-Type",
                "application/json"
        );
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(10000);
        connection.setDoOutput(true);

        JSONObject request = new JSONObject();
        request.put("device_id", deviceId);
        request.put("device_credential", deviceCredential);

        try (OutputStream outputStream = connection.getOutputStream()) {
            outputStream.write(
                    request.toString().getBytes(StandardCharsets.UTF_8)
            );
        }

        int responseCode = connection.getResponseCode();

        InputStream inputStream;

        if (responseCode >= 200 && responseCode < 300) {
            inputStream = connection.getInputStream();
        } else {
            inputStream = connection.getErrorStream();
        }

        String responseBody = readResponse(inputStream);

        connection.disconnect();

        if (responseCode < 200 || responseCode >= 300) {
            throw new Exception(
                    "Backend returned HTTP " +
                    responseCode +
                    ": " +
                    responseBody
            );
        }

        JSONObject response = new JSONObject(responseBody);

        return response.optString("status", "unknown");
    }

    private static String readResponse(InputStream inputStream)
            throws Exception {

        if (inputStream == null) {
            return "";
        }

        StringBuilder response = new StringBuilder();

        try (BufferedReader reader =
                     new BufferedReader(
                             new InputStreamReader(
                                     inputStream,
                                     StandardCharsets.UTF_8
                             )
                     )) {

            String line;

            while ((line = reader.readLine()) != null) {
                response.append(line);
            }
        }

        return response.toString();
    }
}

