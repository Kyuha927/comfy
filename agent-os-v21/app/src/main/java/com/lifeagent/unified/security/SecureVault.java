package com.lifeagent.unified.security;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import com.lifeagent.unified.core.AgentCore;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.util.Locale;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Device-bound encrypted storage. It never accepts authentication secrets or card security data. */
public final class SecureVault {
    private static final String STORE = "life_agent_vault_ciphertext_v2";
    private static final String KEY_ALIAS = "life_agent_os_v21_aes_gcm";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static volatile SecureVault instance;

    private final SharedPreferences preferences;

    private SecureVault(Context context) {
        this.preferences = context.getApplicationContext().getSharedPreferences(STORE, Context.MODE_PRIVATE);
    }

    public static SecureVault get(Context context) {
        SecureVault local = instance;
        if (local == null) {
            synchronized (SecureVault.class) {
                local = instance;
                if (local == null) {
                    local = new SecureVault(context);
                    instance = local;
                }
            }
        }
        return local;
    }

    public synchronized void put(String logicalKey, String value) {
        requireLogicalKey(logicalKey);
        String safeValue = value == null ? "" : value;
        if (isForbiddenSecret(logicalKey, safeValue)) {
            throw new SecurityException("비밀번호·OTP·PIN·CVV·복구코드·개인키는 저장할 수 없습니다.");
        }
        try {
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey());
            byte[] ciphertext = cipher.doFinal(safeValue.getBytes(StandardCharsets.UTF_8));
            String payload = "v1."
                    + Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP | Base64.URL_SAFE)
                    + "."
                    + Base64.encodeToString(ciphertext, Base64.NO_WRAP | Base64.URL_SAFE);
            preferences.edit().putString(storageKey(logicalKey), payload).apply();
        } catch (Exception error) {
            throw new IllegalStateException("암호화 저장에 실패했습니다.", error);
        }
    }

    public synchronized String get(String logicalKey) {
        requireLogicalKey(logicalKey);
        String payload = preferences.getString(storageKey(logicalKey), null);
        if (payload == null || payload.isBlank()) return "";
        try {
            String[] parts = payload.split("\\.", -1);
            if (parts.length != 3 || !"v1".equals(parts[0])) throw new SecurityException("지원하지 않는 금고 형식");
            byte[] iv = Base64.decode(parts[1], Base64.NO_WRAP | Base64.URL_SAFE);
            byte[] ciphertext = Base64.decode(parts[2], Base64.NO_WRAP | Base64.URL_SAFE);
            if (iv.length != 12 || ciphertext.length < 16) throw new SecurityException("손상된 금고 데이터");
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), new GCMParameterSpec(128, iv));
            return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        } catch (SecurityException error) {
            throw error;
        } catch (Exception error) {
            throw new SecurityException("금고 데이터가 손상되었거나 이 기기에서 열 수 없습니다.", error);
        }
    }

    public synchronized void delete(String logicalKey) {
        requireLogicalKey(logicalKey);
        preferences.edit().remove(storageKey(logicalKey)).apply();
    }

    public synchronized void clearAll() {
        preferences.edit().clear().commit();
    }

    public synchronized boolean contains(String logicalKey) {
        requireLogicalKey(logicalKey);
        return preferences.contains(storageKey(logicalKey));
    }

    private static SecretKey getOrCreateKey() throws Exception {
        KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
        keyStore.load(null);
        KeyStore.Entry existing = keyStore.getEntry(KEY_ALIAS, null);
        if (existing instanceof KeyStore.SecretKeyEntry) {
            return ((KeyStore.SecretKeyEntry) existing).getSecretKey();
        }
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        KeyGenParameterSpec spec = new KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT
        )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .setRandomizedEncryptionRequired(true)
                .build();
        generator.init(spec);
        return generator.generateKey();
    }

    private static String storageKey(String logicalKey) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(("life-agent:" + logicalKey).getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder("v2_");
            for (byte value : digest) out.append(String.format(Locale.ROOT, "%02x", value));
            return out.toString();
        } catch (Exception impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    private static void requireLogicalKey(String key) {
        if (key == null || key.isBlank() || key.length() > 160) {
            throw new IllegalArgumentException("유효하지 않은 금고 키입니다.");
        }
    }

    private static boolean isForbiddenSecret(String key, String value) {
        String normalizedKey = AgentCore.normalize(key);
        String normalizedValue = AgentCore.normalize(value);
        String combined = normalizedKey + normalizedValue;
        return AgentCore.looksSensitive(value)
                || combined.contains("password")
                || combined.contains("비밀번호")
                || combined.contains("otp")
                || combined.contains("인증번호")
                || combined.contains("pin")
                || combined.contains("cvv")
                || combined.contains("cvc")
                || combined.contains("복구코드")
                || combined.contains("seedphrase")
                || combined.contains("시드문구")
                || combined.contains("privatekey")
                || combined.contains("개인키");
    }
}
