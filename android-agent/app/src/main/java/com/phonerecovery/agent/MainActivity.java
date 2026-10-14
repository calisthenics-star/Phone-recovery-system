package com.phonerecovery.agent;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.Intent;
import android.content.SharedPreferences;
import android.widget.TextView;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import com.phonerecovery.agent.network.ApiClient;

public class MainActivity extends Activity {

    private TextView textView;
    private ExecutorService executor;
    private Handler mainHandler;

    private static final String PREFS_NAME = "phone_recovery";
    private static final String KEY_DEVICE_ID = "device_id";
    private static final String KEY_DEVICE_CREDENTIAL = "device_credential";

    private static final String EXTRA_DEVICE_ID = "device_id";
    private static final String EXTRA_DEVICE_CREDENTIAL = "device_credential";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        textView = new TextView(this);
        textView.setTextSize(20);
        textView.setPadding(48, 48, 48, 48);
        textView.setText("Phone Recovery\n\nStarting...");
        setContentView(textView);

        executor = Executors.newSingleThreadExecutor();
        mainHandler = new Handler(Looper.getMainLooper());

	handleProvisioningIntent(getIntent());
    }

    /*
     * Provisioning entry point.
     *
     * Later this same flow can be triggered by:
     * - QR enrollment
     * - NFC / secure pairing
     * - Owner-approved provisioning flow
     *
     * For now, device_id and device_credential are accepted
     * through Intent extras so we can test the complete
     * persistence + authentication path without inventing
     * another backend API.
     */
	private void handleProvisioningIntent(Intent intent) {

        String incomingDeviceId =
                intent.getStringExtra(EXTRA_DEVICE_ID);

        String incomingCredential =
                intent.getStringExtra(EXTRA_DEVICE_CREDENTIAL);

        if (incomingDeviceId != null && incomingCredential != null
                && !incomingDeviceId.trim().isEmpty()
                && !incomingCredential.trim().isEmpty()) {

            provisionDevice(
                    incomingDeviceId.trim(),
                    incomingCredential.trim()
            );

            return;
        }

        authenticateDevice();
    }
@Override
protected void onNewIntent(Intent intent) {
    super.onNewIntent(intent);
    setIntent(intent);
    handleProvisioningIntent(intent);
}

    private void provisionDevice(
            String deviceIdString,
            String deviceCredential) {

        int deviceId;

        try {
            deviceId = Integer.parseInt(deviceIdString);
        } catch (NumberFormatException e) {
            textView.setText(
                    "Phone Recovery\n\n" +
                    "Provisioning failed.\n\n" +
                    "Invalid device ID."
            );
            return;
        }

        SharedPreferences prefs =
                getSharedPreferences(PREFS_NAME, MODE_PRIVATE);

        prefs.edit()
                .putString(KEY_DEVICE_ID, String.valueOf(deviceId))
                .putString(KEY_DEVICE_CREDENTIAL, deviceCredential)
                .apply();

        textView.setText(
                "Phone Recovery\n\n" +
                "Device provisioned.\n\n" +
                "Checking device status..."
        );

        authenticateDevice();
    }

    private void authenticateDevice() {

        SharedPreferences prefs =
                getSharedPreferences(PREFS_NAME, MODE_PRIVATE);

        String deviceIdString =
                prefs.getString(KEY_DEVICE_ID, null);

        String deviceCredential =
                prefs.getString(KEY_DEVICE_CREDENTIAL, null);

        if (deviceIdString == null || deviceCredential == null) {

            textView.setText(
                    "Phone Recovery\n\n" +
                    "Device not provisioned.\n\n" +
                    "Device ID and credential are required."
            );

            return;
        }

        int deviceId;

        try {
            deviceId = Integer.parseInt(deviceIdString);
        } catch (NumberFormatException e) {

            textView.setText(
                    "Phone Recovery\n\n" +
                    "Invalid device ID."
            );

            return;
        }

        final int finalDeviceId = deviceId;

        executor.execute(() -> {

            try {

                String status =
                        ApiClient.authenticateDevice(
                                finalDeviceId,
                                deviceCredential
                        );

                mainHandler.post(() -> {

                    if ("lost".equalsIgnoreCase(status)) {

                        textView.setText(
                                "Phone Recovery\n\n" +
                                "⚠ LOST MODE ACTIVE"
                        );

                    } else {

                        textView.setText(
                                "Phone Recovery\n\n" +
                                "Device status: " +
                                status
                        );
                    }
                });

            } catch (Exception e) {

                mainHandler.post(() ->
                        textView.setText(
                                "Phone Recovery\n\n" +
                                "Backend connection failed.\n\n" +
                                e.getMessage()
                        )
                );
            }
        });
    }

    @Override
    protected void onDestroy() {

        super.onDestroy();

        if (executor != null) {
            executor.shutdownNow();
        }
    }
}
