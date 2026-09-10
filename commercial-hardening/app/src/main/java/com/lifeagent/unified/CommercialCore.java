package com.lifeagent.unified;

import android.Manifest;
import android.app.KeyguardManager;
import android.app.NotificationManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.location.Location;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.service.autofill.AutofillService;
import android.service.notification.NotificationListenerService;
import android.text.TextUtils;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Commercial hardening kernel for Life Agent OS.
 *
 * This class intentionally treats unconnected external providers as unavailable. A plan can
 * exist without an execution provider, but a task can never be marked complete without verified
 * external evidence. Sensitive raw notifications are never persisted.
 */
final class CommercialCore {
    static final String VERSION = "3.2.0-hardening-beta";
    static final int SCHEMA = 5;

    static final String PKG_MONIMO = "net.ib.android.smcard";
    static final String PKG_KAKAO = "com.kakao.talk";
    static final String PKG_GOOGLE_MESSAGES = "com.google.android.apps.messaging";
    static final String PKG_SAMSUNG_MESSAGES = "com.samsung.android.messaging";
    static final String PKG_SOOP = "kr.co.nowcom.mobile.afreeca";
    static final String PKG_CHZZK = "com.navercorp.game.android.community";
    static final String PKG_RUSTDESK = "com.carriez.flutter_hbb";

    private static final String STORE_PREFS = "life_agent_commercial_ciphertext_v5";
    private static final String STORE_ALIAS = "life_agent_commercial_aes_v5";
    private static final String STATE_KEY = "agent_state";
    private static final String CURRENT_SUFFIX = ".current";
    private static final String BACKUP_SUFFIX = ".backup";
    private static final String PENDING_SUFFIX = ".pending";

    private static final int MAX_TASKS = 300;
    private static final int MAX_OPPORTUNITIES = 150;
    private static final int MAX_EVENTS = 200;
    private static final long EVENT_TTL_MS = TimeUnit.DAYS.toMillis(14);
    private static final long OPPORTUNITY_TTL_MS = TimeUnit.DAYS.toMillis(30);

    private static final Pattern OTP = Pattern.compile(
            "(?i)(otp|인증번호|인증코드|verification[ ]?code|일회용[ ]?비밀번호).{0,24}?\\b\\d{4,8}\\b");
    private static final Pattern PASSWORD = Pattern.compile(
            "(?i)(password|passwd|비밀번호|간편비밀번호|pin|보안카드|복구코드|seed phrase|private key)");
    private static final Pattern CARD = Pattern.compile("(?<!\\d)(?:\\d[ -]*?){13,19}(?!\\d)");
    private static final Pattern ACCOUNT = Pattern.compile("(?<!\\d)\\d{2,6}[- ]?\\d{2,6}[- ]?\\d{2,8}(?!\\d)");
    private static final Pattern LONG_NUMBER = Pattern.compile("(?<!\\d)\\d{7,}(?!\\d)");

    private CommercialCore() {}

    enum Gate {
        AUTO,
        CONFIRM,
        DEVICE_CREDENTIAL,
        MANUAL_AUTH,
        BLOCK
    }

    enum Executor {
        MODEL_FREE,
        ANDROID_INTENT,
        LOCAL_OCR,
        SAFE_AUTOFILL,
        SUBSCRIPTION_FAST,
        SUBSCRIPTION_DEEP,
        MOBILE_CU,
        DESKTOP_COMPANION,
        HUMAN
    }

    enum Integration {
        READY,
        PARTIAL,
        SETUP_REQUIRED,
        BLOCKED
    }

    enum TaskStatus {
        DRAFT,
        READY,
        RUNNING,
        NEEDS_CONFIRMATION,
        NEEDS_AUTH,
        VERIFYING,
        COMPLETED,
        PROBLEM,
        CANCELLED
    }

    enum OpportunityState {
        NEW,
        SNOOZED,
        ACCEPTED,
        DISMISSED,
        AUTO_RULE_CREATED
    }

    enum EventType {
        INSURANCE_FOLLOWUP,
        BENEFIT_CANDIDATE,
        RESERVATION_CHANGE,
        STREAM_LIVE,
        SOFTWARE_UPDATE,
        DELIVERY,
        GENERAL_ACTION,
        SENSITIVE_DROPPED,
        IGNORED
    }

    static final class StoreException extends Exception {
        StoreException(String message, Throwable cause) {
            super(message, cause);
        }

        StoreException(String message) {
            super(message);
        }
    }

    static final class SecureJsonStore {
        private static final SecureRandom RANDOM = new SecureRandom();

        private SecureJsonStore() {}

        static synchronized JSONObject read(Context context, String key, JSONObject fallback)
                throws StoreException {
            SharedPreferences prefs = context.getSharedPreferences(STORE_PREFS, Context.MODE_PRIVATE);
            String current = prefs.getString(key + CURRENT_SUFFIX, null);
            if (!TextUtils.isEmpty(current)) {
                try {
                    return new JSONObject(decrypt(key, current));
                } catch (Exception currentError) {
                    String backup = prefs.getString(key + BACKUP_SUFFIX, null);
                    if (!TextUtils.isEmpty(backup)) {
                        try {
                            JSONObject recovered = new JSONObject(decrypt(key, backup));
                            if (!prefs.edit().putString(key + CURRENT_SUFFIX, backup).commit()) {
                                throw new StoreException("recovery_commit_failed", currentError);
                            }
                            return recovered;
                        } catch (Exception backupError) {
                            throw new StoreException("encrypted_state_unreadable", backupError);
                        }
                    }
                    throw new StoreException("encrypted_state_unreadable", currentError);
                }
            }
            return cloneJson(fallback);
        }

        static synchronized void write(Context context, String key, JSONObject value)
                throws StoreException {
            if (value == null) throw new StoreException("null_state_rejected");
            SharedPreferences prefs = context.getSharedPreferences(STORE_PREFS, Context.MODE_PRIVATE);
            final String plaintext = value.toString();
            final String envelope;
            try {
                envelope = encrypt(key, plaintext);
                String verified = decrypt(key, envelope);
                if (!plaintext.equals(verified)) throw new StoreException("encryption_roundtrip_failed");
            } catch (StoreException e) {
                throw e;
            } catch (Exception e) {
                throw new StoreException("encryption_failed", e);
            }

            if (!prefs.edit().putString(key + PENDING_SUFFIX, envelope).commit()) {
                throw new StoreException("pending_commit_failed");
            }
            String pending = prefs.getString(key + PENDING_SUFFIX, null);
            if (!envelope.equals(pending)) throw new StoreException("pending_readback_failed");
            try {
                if (!plaintext.equals(decrypt(key, pending))) {
                    throw new StoreException("pending_verification_failed");
                }
            } catch (StoreException e) {
                throw e;
            } catch (Exception e) {
                throw new StoreException("pending_verification_failed", e);
            }

            String previous = prefs.getString(key + CURRENT_SUFFIX, null);
            SharedPreferences.Editor promote = prefs.edit();
            if (!TextUtils.isEmpty(previous)) promote.putString(key + BACKUP_SUFFIX, previous);
            promote.putString(key + CURRENT_SUFFIX, envelope);
            promote.remove(key + PENDING_SUFFIX);
            if (!promote.commit()) throw new StoreException("promotion_commit_failed");

            try {
                String committed = prefs.getString(key + CURRENT_SUFFIX, null);
                if (TextUtils.isEmpty(committed) || !plaintext.equals(decrypt(key, committed))) {
                    throw new StoreException("committed_readback_failed");
                }
            } catch (StoreException e) {
                throw e;
            } catch (Exception e) {
                throw new StoreException("committed_readback_failed", e);
            }
        }

        static synchronized void wipe(Context context) throws StoreException {
            SharedPreferences prefs = context.getSharedPreferences(STORE_PREFS, Context.MODE_PRIVATE);
            if (!prefs.edit().clear().commit()) throw new StoreException("wipe_commit_failed");
            try {
                KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
                keyStore.load(null);
                if (keyStore.containsAlias(STORE_ALIAS)) keyStore.deleteEntry(STORE_ALIAS);
            } catch (Exception e) {
                throw new StoreException("key_wipe_failed", e);
            }
        }

        static boolean selfTest(Context context) {
            String key = "health_" + UUID.randomUUID();
            JSONObject probe = new JSONObject();
            try {
                probe.put("nonce", UUID.randomUUID().toString());
                probe.put("schema", SCHEMA);
                write(context, key, probe);
                JSONObject read = read(context, key, new JSONObject());
                boolean pass = probe.optString("nonce").equals(read.optString("nonce"));
                SharedPreferences prefs = context.getSharedPreferences(STORE_PREFS, Context.MODE_PRIVATE);
                prefs.edit().remove(key + CURRENT_SUFFIX).remove(key + BACKUP_SUFFIX)
                        .remove(key + PENDING_SUFFIX).commit();
                return pass;
            } catch (Exception ignored) {
                return false;
            }
        }

        private static String encrypt(String key, String plaintext) throws Exception {
            byte[] iv = new byte[12];
            RANDOM.nextBytes(iv);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey(), new GCMParameterSpec(128, iv));
            cipher.updateAAD(("LifeAgent:" + key + ":v" + SCHEMA).getBytes(StandardCharsets.UTF_8));
            byte[] ciphertext = cipher.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            JSONObject envelope = new JSONObject();
            envelope.put("v", SCHEMA);
            envelope.put("iv", android.util.Base64.encodeToString(iv, android.util.Base64.NO_WRAP));
            envelope.put("ct", android.util.Base64.encodeToString(ciphertext, android.util.Base64.NO_WRAP));
            return envelope.toString();
        }

        private static String decrypt(String key, String rawEnvelope) throws Exception {
            JSONObject envelope = new JSONObject(rawEnvelope);
            if (envelope.optInt("v", -1) != SCHEMA) throw new StoreException("unsupported_store_schema");
            byte[] iv = android.util.Base64.decode(envelope.getString("iv"), android.util.Base64.NO_WRAP);
            byte[] ciphertext = android.util.Base64.decode(envelope.getString("ct"), android.util.Base64.NO_WRAP);
            if (iv.length != 12 || ciphertext.length < 16) throw new StoreException("invalid_envelope");
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), new GCMParameterSpec(128, iv));
            cipher.updateAAD(("LifeAgent:" + key + ":v" + SCHEMA).getBytes(StandardCharsets.UTF_8));
            return new String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8);
        }

        private static SecretKey getOrCreateKey() throws Exception {
            KeyStore keyStore = KeyStore.getInstance("AndroidKeyStore");
            keyStore.load(null);
            if (keyStore.containsAlias(STORE_ALIAS)) {
                KeyStore.SecretKeyEntry entry = (KeyStore.SecretKeyEntry) keyStore.getEntry(STORE_ALIAS, null);
                return entry.getSecretKey();
            }
            KeyGenerator generator = KeyGenerator.getInstance(
                    android.security.keystore.KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            android.security.keystore.KeyGenParameterSpec spec =
                    new android.security.keystore.KeyGenParameterSpec.Builder(
                            STORE_ALIAS,
                            android.security.keystore.KeyProperties.PURPOSE_ENCRYPT
                                    | android.security.keystore.KeyProperties.PURPOSE_DECRYPT)
                            .setBlockModes(android.security.keystore.KeyProperties.BLOCK_MODE_GCM)
                            .setEncryptionPaddings(android.security.keystore.KeyProperties.ENCRYPTION_PADDING_NONE)
                            .setKeySize(256)
                            .setRandomizedEncryptionRequired(true)
                            .build();
            generator.init(spec);
            return generator.generateKey();
        }
    }

    static final class SettingsState {
        boolean notificationAnalysis;
        boolean nearbyOpportunities;
        boolean commercialRecommendations;
        boolean updateChecks;
        boolean exactStreamAutoOpen;
        long locationSessionEndMs;
        final Set<String> allowedPackages = new LinkedHashSet<>();
        final List<StreamRule> streamRules = new ArrayList<>();
        final Set<String> disabledOpportunityCategories = new LinkedHashSet<>();

        JSONObject toJson() throws JSONException {
            JSONObject json = new JSONObject();
            json.put("notificationAnalysis", notificationAnalysis);
            json.put("nearbyOpportunities", nearbyOpportunities);
            json.put("commercialRecommendations", commercialRecommendations);
            json.put("updateChecks", updateChecks);
            json.put("exactStreamAutoOpen", exactStreamAutoOpen);
            json.put("locationSessionEndMs", locationSessionEndMs);
            json.put("allowedPackages", jsonArray(allowedPackages));
            JSONArray rules = new JSONArray();
            for (StreamRule rule : streamRules) rules.put(rule.toJson());
            json.put("streamRules", rules);
            json.put("disabledOpportunityCategories", jsonArray(disabledOpportunityCategories));
            return json;
        }

        static SettingsState from(JSONObject json) {
            SettingsState state = new SettingsState();
            if (json == null) return state;
            state.notificationAnalysis = json.optBoolean("notificationAnalysis", false);
            state.nearbyOpportunities = json.optBoolean("nearbyOpportunities", false);
            state.commercialRecommendations = json.optBoolean("commercialRecommendations", false);
            state.updateChecks = json.optBoolean("updateChecks", false);
            state.exactStreamAutoOpen = json.optBoolean("exactStreamAutoOpen", false);
            state.locationSessionEndMs = json.optLong("locationSessionEndMs", 0L);
            addStrings(state.allowedPackages, json.optJSONArray("allowedPackages"));
            JSONArray rules = json.optJSONArray("streamRules");
            if (rules != null) {
                for (int i = 0; i < rules.length(); i++) {
                    StreamRule rule = StreamRule.from(rules.optJSONObject(i));
                    if (rule != null) state.streamRules.add(rule);
                }
            }
            addStrings(state.disabledOpportunityCategories,
                    json.optJSONArray("disabledOpportunityCategories"));
            return state;
        }
    }

    static final class ProfileState {
        String displayName = "";
        String email = "";
        String phone = "";
        String address = "";
        String healthNotes = "";
        String interestTags = "";
        String benefitNotes = "";

        JSONObject toJson() throws JSONException {
            JSONObject json = new JSONObject();
            json.put("displayName", clipped(displayName, 80));
            json.put("email", clipped(email, 160));
            json.put("phone", clipped(phone, 40));
            json.put("address", clipped(address, 240));
            json.put("healthNotes", clipped(healthNotes, 1200));
            json.put("interestTags", clipped(interestTags, 600));
            json.put("benefitNotes", clipped(benefitNotes, 1200));
            return json;
        }

        static ProfileState from(JSONObject json) {
            ProfileState state = new ProfileState();
            if (json == null) return state;
            state.displayName = json.optString("displayName", "");
            state.email = json.optString("email", "");
            state.phone = json.optString("phone", "");
            state.address = json.optString("address", "");
            state.healthNotes = json.optString("healthNotes", "");
            state.interestTags = json.optString("interestTags", "");
            state.benefitNotes = json.optString("benefitNotes", "");
            return state;
        }

        boolean hasHealthOrSupplementContext() {
            String joined = (healthNotes + " " + interestTags).toLowerCase(Locale.ROOT);
            return containsAny(joined, "영양제", "비타민", "약", "통풍", "피부", "건강", "병원");
        }
    }

    static final class StreamRule {
        String platform;
        String alias;
        String channelUrl;

        JSONObject toJson() throws JSONException {
            JSONObject json = new JSONObject();
            json.put("platform", clipped(platform, 20));
            json.put("alias", clipped(alias, 100));
            json.put("channelUrl", clipped(channelUrl, 500));
            return json;
        }

        static StreamRule from(JSONObject json) {
            if (json == null) return null;
            StreamRule rule = new StreamRule();
            rule.platform = json.optString("platform", "");
            rule.alias = normalize(json.optString("alias", ""));
            rule.channelUrl = json.optString("channelUrl", "");
            if (!("soop".equals(rule.platform) || "chzzk".equals(rule.platform))) return null;
            if (rule.alias.length() < 2 || !isAllowedChannelUrl(rule.platform, rule.channelUrl)) return null;
            return rule;
        }
    }

    static final class EventRecord {
        String id;
        long createdAt;
        String sourcePackage;
        EventType type;
        String safeSummary;
        String dedupHash;

        JSONObject toJson() throws JSONException {
            JSONObject json = new JSONObject();
            json.put("id", id);
            json.put("createdAt", createdAt);
            json.put("sourcePackage", sourcePackage);
            json.put("type", type.name());
            json.put("safeSummary", safeSummary);
            json.put("dedupHash", dedupHash);
            return json;
        }

        static EventRecord from(JSONObject json) {
            if (json == null) return null;
            EventRecord record = new EventRecord();
            record.id = json.optString("id", "");
            record.createdAt = json.optLong("createdAt", 0L);
            record.sourcePackage = json.optString("sourcePackage", "");
            try {
                record.type = EventType.valueOf(json.optString("type", "IGNORED"));
            } catch (IllegalArgumentException e) {
                record.type = EventType.IGNORED;
            }
            record.safeSummary = json.optString("safeSummary", "");
            record.dedupHash = json.optString("dedupHash", "");
            return record.id.isEmpty() ? null : record;
        }
    }

    static final class TaskRecord {
        String id;
        long createdAt;
        long updatedAt;
        String goal;
        String skillId;
        Gate gate;
        Executor executor;
        Integration integration;
        TaskStatus status;
        String nextAction;
        String verificationType;
        String evidence;
        String failureCode;
        int attempts;
        final List<String> steps = new ArrayList<>();

        JSONObject toJson() throws JSONException {
            JSONObject json = new JSONObject();
            json.put("id", id);
            json.put("createdAt", createdAt);
            json.put("updatedAt", updatedAt);
            json.put("goal", clipped(redact(goal), 600));
            json.put("skillId", skillId);
            json.put("gate", gate.name());
            json.put("executor", executor.name());
            json.put("integration", integration.name());
            json.put("status", status.name());
            json.put("nextAction", clipped(nextAction, 300));
            json.put("verificationType", verificationType);
            json.put("evidence", clipped(redact(evidence), 400));
            json.put("failureCode", clipped(failureCode, 80));
            json.put("attempts", attempts);
            json.put("steps", jsonArray(steps));
            return json;
        }

        static TaskRecord from(JSONObject json) {
            if (json == null) return null;
            TaskRecord task = new TaskRecord();
            task.id = json.optString("id", "");
            task.createdAt = json.optLong("createdAt", 0L);
            task.updatedAt = json.optLong("updatedAt", 0L);
            task.goal = json.optString("goal", "");
            task.skillId = json.optString("skillId", "general.delegate");
            task.gate = enumValue(Gate.class, json.optString("gate", "CONFIRM"), Gate.CONFIRM);
            task.executor = enumValue(Executor.class, json.optString("executor", "HUMAN"), Executor.HUMAN);
            task.integration = enumValue(Integration.class,
                    json.optString("integration", "SETUP_REQUIRED"), Integration.SETUP_REQUIRED);
            task.status = enumValue(TaskStatus.class,
                    json.optString("status", "DRAFT"), TaskStatus.DRAFT);
            task.nextAction = json.optString("nextAction", "");
            task.verificationType = json.optString("verificationType", "explicit_user_result");
            task.evidence = json.optString("evidence", "");
            task.failureCode = json.optString("failureCode", "");
            task.attempts = Math.max(0, json.optInt("attempts", 0));
            addStrings(task.steps, json.optJSONArray("steps"));
            return task.id.isEmpty() ? null : task;
        }

        boolean canComplete() {
            return !TextUtils.isEmpty(verificationType)
                    && !"none".equals(verificationType)
                    && !TextUtils.isEmpty(evidence)
                    && integration != Integration.BLOCKED;
        }
    }

    static final class OpportunityRecord {
        String id;
        long createdAt;
        long snoozeUntil;
        String category;
        String title;
        String reason;
        String actionLabel;
        String skillId;
        String sourcePackage;
        boolean sponsored;
        OpportunityState state;

        JSONObject toJson() throws JSONException {
            JSONObject json = new JSONObject();
            json.put("id", id);
            json.put("createdAt", createdAt);
            json.put("snoozeUntil", snoozeUntil);
            json.put("category", clipped(category, 60));
            json.put("title", clipped(title, 180));
            json.put("reason", clipped(redact(reason), 500));
            json.put("actionLabel", clipped(actionLabel, 80));
            json.put("skillId", skillId);
            json.put("sourcePackage", sourcePackage);
            json.put("sponsored", sponsored);
            json.put("state", state.name());
            return json;
        }

        static OpportunityRecord from(JSONObject json) {
            if (json == null) return null;
            OpportunityRecord opportunity = new OpportunityRecord();
            opportunity.id = json.optString("id", "");
            opportunity.createdAt = json.optLong("createdAt", 0L);
            opportunity.snoozeUntil = json.optLong("snoozeUntil", 0L);
            opportunity.category = json.optString("category", "general");
            opportunity.title = json.optString("title", "");
            opportunity.reason = json.optString("reason", "");
            opportunity.actionLabel = json.optString("actionLabel", "확인");
            opportunity.skillId = json.optString("skillId", "general.delegate");
            opportunity.sourcePackage = json.optString("sourcePackage", "");
            opportunity.sponsored = json.optBoolean("sponsored", false);
            opportunity.state = enumValue(OpportunityState.class,
                    json.optString("state", "NEW"), OpportunityState.NEW);
            return opportunity.id.isEmpty() ? null : opportunity;
        }
    }

    static final class AppState {
        int schema = SCHEMA;
        long revision;
        SettingsState settings = new SettingsState();
        ProfileState profile = new ProfileState();
        final List<EventRecord> events = new ArrayList<>();
        final List<TaskRecord> tasks = new ArrayList<>();
        final List<OpportunityRecord> opportunities = new ArrayList<>();
        String lastStoreError = "";

        JSONObject toJson() throws JSONException {
            prune();
            JSONObject json = new JSONObject();
            json.put("schema", schema);
            json.put("revision", revision);
            json.put("settings", settings.toJson());
            json.put("profile", profile.toJson());
            JSONArray eventArray = new JSONArray();
            for (EventRecord event : events) eventArray.put(event.toJson());
            json.put("events", eventArray);
            JSONArray taskArray = new JSONArray();
            for (TaskRecord task : tasks) taskArray.put(task.toJson());
            json.put("tasks", taskArray);
            JSONArray opportunityArray = new JSONArray();
            for (OpportunityRecord opportunity : opportunities) opportunityArray.put(opportunity.toJson());
            json.put("opportunities", opportunityArray);
            return json;
        }

        static AppState from(JSONObject json) {
            AppState state = new AppState();
            if (json == null) return state;
            int incomingSchema = json.optInt("schema", SCHEMA);
            if (incomingSchema > SCHEMA) {
                state.lastStoreError = "newer_schema_detected";
                return state;
            }
            state.schema = SCHEMA;
            state.revision = Math.max(0L, json.optLong("revision", 0L));
            state.settings = SettingsState.from(json.optJSONObject("settings"));
            state.profile = ProfileState.from(json.optJSONObject("profile"));
            readEvents(state.events, json.optJSONArray("events"));
            readTasks(state.tasks, json.optJSONArray("tasks"));
            readOpportunities(state.opportunities, json.optJSONArray("opportunities"));
            state.prune();
            return state;
        }

        void prune() {
            long now = System.currentTimeMillis();
            events.removeIf(event -> event == null || now - event.createdAt > EVENT_TTL_MS);
            opportunities.removeIf(item -> item == null
                    || (item.state == OpportunityState.DISMISSED && now - item.createdAt > TimeUnit.DAYS.toMillis(2))
                    || now - item.createdAt > OPPORTUNITY_TTL_MS);
            tasks.sort(Comparator.comparingLong((TaskRecord task) -> task.updatedAt).reversed());
            opportunities.sort(Comparator.comparingLong((OpportunityRecord item) -> item.createdAt).reversed());
            events.sort(Comparator.comparingLong((EventRecord item) -> item.createdAt).reversed());
            trim(tasks, MAX_TASKS);
            trim(opportunities, MAX_OPPORTUNITIES);
            trim(events, MAX_EVENTS);
        }
    }

    static synchronized AppState load(Context context) throws StoreException {
        JSONObject empty = new JSONObject();
        try {
            empty.put("schema", SCHEMA);
            empty.put("revision", 0);
        } catch (JSONException impossible) {
            throw new StoreException("json_initialization_failed", impossible);
        }
        return AppState.from(SecureJsonStore.read(context, STATE_KEY, empty));
    }

    static synchronized void save(Context context, AppState state) throws StoreException {
        if (state == null) throw new StoreException("null_app_state_rejected");
        state.schema = SCHEMA;
        state.revision = Math.max(0L, state.revision) + 1L;
        try {
            SecureJsonStore.write(context, STATE_KEY, state.toJson());
            state.lastStoreError = "";
        } catch (JSONException e) {
            throw new StoreException("state_serialization_failed", e);
        }
    }

    static final class Plan {
        String goal;
        String skillId;
        String title;
        String subtitle;
        Gate gate;
        Executor executor;
        Integration integration;
        String verificationType;
        String nextAction;
        final List<String> steps = new ArrayList<>();

        TaskRecord createTask() {
            long now = System.currentTimeMillis();
            TaskRecord task = new TaskRecord();
            task.id = UUID.randomUUID().toString();
            task.createdAt = now;
            task.updatedAt = now;
            task.goal = clipped(redact(goal), 600);
            task.skillId = skillId;
            task.gate = gate;
            task.executor = executor;
            task.integration = integration;
            task.verificationType = verificationType;
            task.nextAction = nextAction;
            task.steps.addAll(steps);
            if (gate == Gate.BLOCK) task.status = TaskStatus.PROBLEM;
            else if (gate == Gate.MANUAL_AUTH || gate == Gate.DEVICE_CREDENTIAL) task.status = TaskStatus.NEEDS_AUTH;
            else if (gate == Gate.CONFIRM) task.status = TaskStatus.NEEDS_CONFIRMATION;
            else task.status = TaskStatus.READY;
            return task;
        }
    }

    static final class Planner {
        private Planner() {}

        static Plan plan(Context context, String rawGoal, AppState state) {
            String goal = clipped(redact(rawGoal == null ? "" : rawGoal.trim()), 600);
            Plan plan = new Plan();
            plan.goal = goal;
            String normalized = normalize(goal);
            if (looksSensitive(rawGoal)) {
                plan.skillId = "security.manual_auth";
                plan.title = "민감정보 직접 처리";
                plan.subtitle = "인증번호·비밀번호·카드 보안정보는 저장하거나 자동 처리하지 않습니다.";
                plan.gate = Gate.BLOCK;
                plan.executor = Executor.HUMAN;
                plan.integration = Integration.BLOCKED;
                plan.verificationType = "none";
                plan.nextAction = "민감정보를 지우고 목표만 다시 입력하세요.";
                plan.steps.add("민감정보 폐기");
                plan.steps.add("사용자가 공식 앱에서 직접 인증");
                return plan;
            }

            if (containsAny(normalized, "예약", "병원", "식당", "미용실", "전화해")) {
                plan.skillId = "reservation.orchestrator";
                plan.title = "예약 대행";
                plan.subtitle = "공식 웹·앱을 우선하고, 없으면 전화 초안을 준비합니다.";
                plan.gate = Gate.CONFIRM;
                plan.executor = Executor.ANDROID_INTENT;
                plan.integration = Integration.PARTIAL;
                plan.verificationType = "reservation_confirmation";
                plan.nextAction = "장소·날짜·시간을 확인한 뒤 공식 경로 또는 전화 앱을 엽니다.";
                Collections.addAll(plan.steps,
                        "예약 대상과 조건 확인",
                        "공식 웹·앱·전화 경로 선택",
                        "사용자 확인",
                        "예약 확인번호 또는 확인 메시지 검증");
                return plan;
            }

            if (containsAny(normalized, "보험", "모니모", "진료비", "추가서류", "청구")) {
                plan.skillId = "insurance.claim.monimo";
                plan.title = "보험금 청구";
                plan.subtitle = "서류 준비와 모니모 실행을 연결하되 제출은 확인 뒤 진행합니다.";
                plan.gate = Gate.CONFIRM;
                plan.executor = isPackageInstalled(context, PKG_MONIMO)
                        ? Executor.ANDROID_INTENT : Executor.HUMAN;
                plan.integration = isPackageInstalled(context, PKG_MONIMO)
                        ? Integration.PARTIAL : Integration.SETUP_REQUIRED;
                plan.verificationType = "claim_receipt_number";
                plan.nextAction = isPackageInstalled(context, PKG_MONIMO)
                        ? "서류를 확인한 뒤 모니모를 엽니다. 접수번호가 있어야 완료됩니다."
                        : "모니모 설치 또는 공식 보험사 연동이 필요합니다.";
                Collections.addAll(plan.steps,
                        "서류 종류와 품질 확인",
                        "환자·진료일·병원 정보 교차 확인",
                        "모니모에서 본인인증",
                        "제출 직전 사용자 확인",
                        "접수번호 검증");
                return plan;
            }

            if (containsAny(normalized, "송금", "보내줘", "입금", "이체")) {
                plan.skillId = "transfer.secure";
                plan.title = "안전 송금";
                plan.subtitle = "수취인과 금액 초안만 만들며 정식 금융 제공자가 없으면 실행하지 않습니다.";
                plan.gate = Gate.DEVICE_CREDENTIAL;
                plan.executor = Executor.HUMAN;
                plan.integration = Integration.SETUP_REQUIRED;
                plan.verificationType = "provider_transaction_receipt";
                plan.nextAction = "정식 은행·오픈뱅킹 제공자 연결과 기기 인증이 필요합니다.";
                Collections.addAll(plan.steps,
                        "수취인·금액·통화 확인",
                        "중복·한도 검사",
                        "기기 인증",
                        "은행 앱 또는 정식 제공자 인증",
                        "거래 영수증 검증");
                return plan;
            }

            if (containsAny(normalized, "회원가입", "가입해", "폼", "자동입력")) {
                plan.skillId = "identity.signup";
                plan.title = "회원가입·안전 자동입력";
                plan.subtitle = "허용한 일반 개인정보만 채우며 비밀번호와 OTP는 제외합니다.";
                plan.gate = Gate.CONFIRM;
                plan.executor = Executor.SAFE_AUTOFILL;
                plan.integration = isAutofillEnabled(context)
                        ? Integration.PARTIAL : Integration.SETUP_REQUIRED;
                plan.verificationType = "account_creation_receipt";
                plan.nextAction = isAutofillEnabled(context)
                        ? "대상 사이트와 입력 필드를 확인하세요."
                        : "Life Agent 안전 자동입력 서비스를 먼저 켜야 합니다.";
                Collections.addAll(plan.steps,
                        "대상 앱·도메인 확인",
                        "필드 의미와 신뢰도 검사",
                        "허용된 개인정보만 채우기",
                        "비밀번호·OTP는 사용자 직접 입력",
                        "가입 완료 화면 확인");
                return plan;
            }

            if (containsAny(normalized, "방송", "스트리머", "치지직", "soop", "숲")) {
                plan.skillId = "stream.autoopen";
                plan.title = "방송 자동 실행";
                plan.subtitle = "정확한 플랫폼·생방송 문구·별칭이 모두 일치할 때만 모델 없이 실행합니다.";
                plan.gate = Gate.CONFIRM;
                plan.executor = Executor.MODEL_FREE;
                plan.integration = isNotificationListenerEnabled(context)
                        ? Integration.READY : Integration.SETUP_REQUIRED;
                plan.verificationType = "target_app_opened";
                plan.nextAction = "알림 접근과 스트리머 규칙을 설정하세요.";
                Collections.addAll(plan.steps,
                        "플랫폼 앱 확인",
                        "생방송 문구 확인",
                        "등록 별칭 정확히 1건 매칭",
                        "원본 알림 실행",
                        "실패 시 수동 알림 표시");
                return plan;
            }

            if (containsAny(normalized, "rustdesk", "업데이트", "새버전", "버전확인")) {
                plan.skillId = "software.update.monitor";
                plan.title = "소프트웨어 업데이트 확인";
                plan.subtitle = "사용자가 요청했을 때 공식 안정판 메타데이터만 확인합니다.";
                plan.gate = Gate.AUTO;
                plan.executor = Executor.ANDROID_INTENT;
                plan.integration = Integration.READY;
                plan.verificationType = "official_release_metadata";
                plan.nextAction = "공식 릴리스 정보를 확인합니다. 자동 설치는 하지 않습니다.";
                Collections.addAll(plan.steps,
                        "설치 버전 확인",
                        "공식 안정판 메타데이터 확인",
                        "버전 비교",
                        "업데이트가 있으면 사용자에게 안내");
                return plan;
            }

            if (containsAny(normalized, "지원금", "지원사업", "혜택", "바우처", "할인", "복지")) {
                plan.skillId = "benefit.autopilot";
                plan.title = "혜택·지원 후보 확인";
                plan.subtitle = "자격을 확정하지 않고 후보와 필요한 서류를 먼저 검토합니다.";
                plan.gate = Gate.CONFIRM;
                plan.executor = Executor.SUBSCRIPTION_DEEP;
                plan.integration = Integration.SETUP_REQUIRED;
                plan.verificationType = "official_application_receipt";
                plan.nextAction = "공식 데이터 제공자와 신청 어댑터 연결이 필요합니다.";
                Collections.addAll(plan.steps,
                        "사용자 조건과 공고 시점 확인",
                        "후보 자격과 근거 표시",
                        "필요서류 체크리스트 생성",
                        "공식 신청 화면에서 사용자 확인",
                        "접수번호 검증");
                return plan;
            }

            if (containsAny(normalized, "근처", "주변", "약국", "가게", "상가")) {
                plan.skillId = "nearby.opportunity";
                plan.title = "주변 기회 찾기";
                plan.subtitle = "정확한 장소를 미리 단정하지 않고 현재 위치에서 지도 검색을 준비합니다.";
                plan.gate = Gate.CONFIRM;
                plan.executor = Executor.ANDROID_INTENT;
                plan.integration = state.settings.nearbyOpportunities
                        ? Integration.READY : Integration.SETUP_REQUIRED;
                plan.verificationType = "user_selected_place";
                plan.nextAction = state.settings.nearbyOpportunities
                        ? "현재 위치를 한 번 확인한 뒤 지도 검색을 엽니다."
                        : "주변 기회 감지를 먼저 켜야 합니다.";
                Collections.addAll(plan.steps,
                        "위치 사용 동의 확인",
                        "대략적 위치만 사용",
                        "사용자 관심과 현재 목표 연결",
                        "지도 앱에서 결과 확인",
                        "선택한 장소만 작업으로 연결");
                return plan;
            }

            plan.skillId = "general.delegate";
            plan.title = "일반 업무 위임";
            plan.subtitle = "문맥을 정리하고 사용 가능한 실행기를 찾습니다.";
            plan.gate = Gate.CONFIRM;
            plan.executor = Executor.SUBSCRIPTION_FAST;
            plan.integration = Integration.SETUP_REQUIRED;
            plan.verificationType = "explicit_user_result";
            plan.nextAction = "AI 구독 실행기 또는 PC Companion 연결이 필요합니다.";
            Collections.addAll(plan.steps,
                    "목표와 제약 확인",
                    "가장 안전하고 저렴한 실행기 선택",
                    "실행 전 확인",
                    "외부 결과 검증");
            return plan;
        }
    }

    static final class NotificationDecision {
        EventType type;
        boolean accepted;
        boolean sensitive;
        String safeSummary;
        String reason;
        StreamRule exactStreamRule;
    }

    static NotificationDecision classifyNotification(
            AppState state, String packageName, String title, String text) {
        NotificationDecision decision = new NotificationDecision();
        decision.type = EventType.IGNORED;
        decision.safeSummary = "";
        decision.reason = "not_allowed";
        if (state == null || !state.settings.notificationAnalysis) return decision;
        if (TextUtils.isEmpty(packageName) || !state.settings.allowedPackages.contains(packageName)) {
            return decision;
        }
        String raw = (safe(title) + " " + safe(text)).trim();
        if (raw.isEmpty()) return decision;
        if (looksSensitive(raw)) {
            decision.sensitive = true;
            decision.type = EventType.SENSITIVE_DROPPED;
            decision.reason = "sensitive_content_dropped";
            return decision;
        }

        String normalized = normalize(raw);
        decision.safeSummary = clipped(redact(raw), 180);
        decision.accepted = true;
        decision.reason = "allowed_package_and_actionable_content";

        if (containsAny(normalized, "추가서류", "보험금", "보험청구", "보상", "접수번호")) {
            decision.type = EventType.INSURANCE_FOLLOWUP;
        } else if (containsAny(normalized, "지원금", "바우처", "혜택", "지원대상", "신청기간", "복지")) {
            decision.type = EventType.BENEFIT_CANDIDATE;
        } else if (containsAny(normalized, "예약취소", "예약변경", "예약확정", "예약완료")) {
            decision.type = EventType.RESERVATION_CHANGE;
        } else if ((PKG_SOOP.equals(packageName) || PKG_CHZZK.equals(packageName))
                && containsAny(normalized, "방송시작", "생방송", "라이브시작", "isnowlive", "startedstreaming")) {
            decision.type = EventType.STREAM_LIVE;
            decision.exactStreamRule = exactStreamRule(state.settings, packageName, normalized);
        } else if (containsAny(normalized, "업데이트", "새버전", "newversion")) {
            decision.type = EventType.SOFTWARE_UPDATE;
        } else if (containsAny(normalized, "배송", "도착", "택배")) {
            decision.type = EventType.DELIVERY;
        } else {
            decision.type = EventType.GENERAL_ACTION;
        }
        return decision;
    }

    static synchronized OpportunityRecord ingestNotification(
            Context context, String packageName, String title, String text) throws StoreException {
        AppState state = load(context);
        NotificationDecision decision = classifyNotification(state, packageName, title, text);
        if (!decision.accepted) return null;
        String hash = sha256(packageName + "|" + decision.type.name() + "|" + decision.safeSummary);
        long now = System.currentTimeMillis();
        for (EventRecord existing : state.events) {
            if (hash.equals(existing.dedupHash) && now - existing.createdAt < TimeUnit.MINUTES.toMillis(10)) {
                return null;
            }
        }

        EventRecord event = new EventRecord();
        event.id = UUID.randomUUID().toString();
        event.createdAt = now;
        event.sourcePackage = packageName;
        event.type = decision.type;
        event.safeSummary = decision.safeSummary;
        event.dedupHash = hash;
        state.events.add(0, event);

        OpportunityRecord opportunity = opportunityFromDecision(decision, packageName, now);
        if (opportunity != null
                && !state.settings.disabledOpportunityCategories.contains(opportunity.category)) {
            state.opportunities.add(0, opportunity);
        } else {
            opportunity = null;
        }
        save(context, state);
        return opportunity;
    }

    private static OpportunityRecord opportunityFromDecision(
            NotificationDecision decision, String packageName, long now) {
        OpportunityRecord opportunity = new OpportunityRecord();
        opportunity.id = UUID.randomUUID().toString();
        opportunity.createdAt = now;
        opportunity.snoozeUntil = 0L;
        opportunity.sourcePackage = packageName;
        opportunity.sponsored = false;
        opportunity.state = OpportunityState.NEW;
        switch (decision.type) {
            case INSURANCE_FOLLOWUP:
                opportunity.category = "insurance";
                opportunity.title = "보험 청구 후속 확인이 필요할 수 있습니다";
                opportunity.reason = "허용한 앱의 보험·추가서류 알림에서 감지했습니다. 공식 청구 화면에서 같은 접수 건인지 다시 확인합니다.";
                opportunity.actionLabel = "후속 계획 보기";
                opportunity.skillId = "insurance.claim.monimo";
                return opportunity;
            case BENEFIT_CANDIDATE:
                opportunity.category = "benefit";
                opportunity.title = "신청 가능한 혜택 후보가 도착했습니다";
                opportunity.reason = "허용한 앱에서 지원·혜택 관련 문구를 감지했습니다. 자격 확정이 아니라 검토 후보입니다.";
                opportunity.actionLabel = "후보 검토";
                opportunity.skillId = "benefit.autopilot";
                return opportunity;
            case RESERVATION_CHANGE:
                opportunity.category = "reservation";
                opportunity.title = "예약 상태가 변경됐을 수 있습니다";
                opportunity.reason = "허용한 앱의 예약 확인·변경 알림을 감지했습니다.";
                opportunity.actionLabel = "예약 확인";
                opportunity.skillId = "reservation.orchestrator";
                return opportunity;
            case STREAM_LIVE:
                opportunity.category = "stream";
                opportunity.title = decision.exactStreamRule == null
                        ? "등록되지 않은 방송 알림이 도착했습니다"
                        : decision.exactStreamRule.alias + " 방송이 시작됐습니다";
                opportunity.reason = decision.exactStreamRule == null
                        ? "플랫폼과 생방송 문구는 맞지만 등록 별칭이 정확히 한 건 일치하지 않았습니다."
                        : "사용자가 등록한 플랫폼·생방송 문구·스트리머 별칭이 정확히 한 건 일치했습니다.";
                opportunity.actionLabel = "방송 열기";
                opportunity.skillId = "stream.autoopen";
                return opportunity;
            case SOFTWARE_UPDATE:
                opportunity.category = "update";
                opportunity.title = "소프트웨어 업데이트 알림이 있습니다";
                opportunity.reason = "허용한 앱의 업데이트 문구를 감지했습니다. 공식 배포처를 별도로 확인해야 합니다.";
                opportunity.actionLabel = "업데이트 확인";
                opportunity.skillId = "software.update.monitor";
                return opportunity;
            default:
                return null;
        }
    }

    static synchronized void addNearbyPharmacyOpportunity(
            Context context, Location location) throws StoreException {
        if (location == null) return;
        AppState state = load(context);
        if (!state.settings.nearbyOpportunities || !state.profile.hasHealthOrSupplementContext()) return;
        double roundedLat = Math.round(location.getLatitude() * 1000d) / 1000d;
        double roundedLon = Math.round(location.getLongitude() * 1000d) / 1000d;
        String dedup = "nearby_pharmacy:" + roundedLat + ":" + roundedLon;
        long now = System.currentTimeMillis();
        for (OpportunityRecord existing : state.opportunities) {
            if ("nearby_pharmacy".equals(existing.category)
                    && existing.reason.contains(dedup)
                    && now - existing.createdAt < TimeUnit.HOURS.toMillis(6)) return;
        }
        OpportunityRecord opportunity = new OpportunityRecord();
        opportunity.id = UUID.randomUUID().toString();
        opportunity.createdAt = now;
        opportunity.category = "nearby_pharmacy";
        opportunity.title = "현재 위치에서 주변 약국을 검색할 수 있습니다";
        opportunity.reason = "최근 저장한 건강·영양제 관심과 사용자가 켠 주변 기회 감지를 연결했습니다. "
                + dedup + " 정확한 이동 기록은 저장하지 않습니다.";
        opportunity.actionLabel = "지도에서 검색";
        opportunity.skillId = "nearby.opportunity";
        opportunity.state = OpportunityState.NEW;
        opportunity.sponsored = false;
        state.opportunities.add(0, opportunity);
        save(context, state);
    }

    static synchronized TaskRecord createTask(Context context, Plan plan) throws StoreException {
        if (plan == null) throw new StoreException("null_plan_rejected");
        AppState state = load(context);
        TaskRecord task = plan.createTask();
        state.tasks.add(0, task);
        save(context, state);
        return task;
    }

    static synchronized boolean completeTask(
            Context context, String taskId, String externalEvidence) throws StoreException {
        AppState state = load(context);
        TaskRecord task = findTask(state, taskId);
        if (task == null) return false;
        task.evidence = clipped(redact(externalEvidence), 400);
        task.updatedAt = System.currentTimeMillis();
        if (!task.canComplete()) {
            task.status = TaskStatus.VERIFYING;
            task.nextAction = "외부 완료 증거를 확인해야 합니다.";
            task.failureCode = "MISSING_VERIFIED_EVIDENCE";
            save(context, state);
            return false;
        }
        task.status = TaskStatus.COMPLETED;
        task.nextAction = "완료 증거가 저장되었습니다.";
        task.failureCode = "";
        save(context, state);
        return true;
    }

    static synchronized void markTaskProblem(
            Context context, String taskId, String failureCode, String nextAction) throws StoreException {
        AppState state = load(context);
        TaskRecord task = findTask(state, taskId);
        if (task == null) return;
        task.status = TaskStatus.PROBLEM;
        task.attempts += 1;
        task.failureCode = clipped(failureCode, 80);
        task.nextAction = clipped(nextAction, 300);
        task.updatedAt = System.currentTimeMillis();
        if (task.attempts >= 3 && task.executor != Executor.HUMAN) {
            task.executor = Executor.HUMAN;
            task.nextAction = "반복 실패로 사용자 확인이 필요합니다.";
        }
        save(context, state);
    }

    static synchronized void updateOpportunity(
            Context context, String id, OpportunityState newState, long snoozeUntil) throws StoreException {
        AppState state = load(context);
        for (OpportunityRecord opportunity : state.opportunities) {
            if (opportunity.id.equals(id)) {
                opportunity.state = newState;
                opportunity.snoozeUntil = snoozeUntil;
                save(context, state);
                return;
            }
        }
    }

    static synchronized void disableOpportunityCategory(Context context, String category)
            throws StoreException {
        AppState state = load(context);
        state.settings.disabledOpportunityCategories.add(category);
        for (OpportunityRecord item : state.opportunities) {
            if (category.equals(item.category)) item.state = OpportunityState.DISMISSED;
        }
        save(context, state);
    }

    static TaskRecord findTask(AppState state, String id) {
        if (state == null || TextUtils.isEmpty(id)) return null;
        for (TaskRecord task : state.tasks) if (id.equals(task.id)) return task;
        return null;
    }

    static OpportunityRecord findOpportunity(AppState state, String id) {
        if (state == null || TextUtils.isEmpty(id)) return null;
        for (OpportunityRecord opportunity : state.opportunities) {
            if (id.equals(opportunity.id)) return opportunity;
        }
        return null;
    }

    static Intent launchSkillIntent(Context context, TaskRecord task) {
        if (task == null) return null;
        String className;
        switch (task.skillId) {
            case "reservation.orchestrator":
                className = "com.lifeagent.unified.ReservationActivity";
                break;
            case "insurance.claim.monimo":
                if (isPackageInstalled(context, PKG_MONIMO)) {
                    return context.getPackageManager().getLaunchIntentForPackage(PKG_MONIMO);
                }
                className = "com.lifeagent.unified.InsuranceActivity";
                break;
            case "transfer.secure":
                className = "com.lifeagent.unified.TransferActivity";
                break;
            case "identity.signup":
                className = "com.lifeagent.unified.SignupActivity";
                break;
            case "stream.autoopen":
                className = "com.lifeagent.unified.StreamRulesActivity";
                break;
            case "software.update.monitor":
                className = "com.lifeagent.unified.RustDeskActivity";
                break;
            case "profile.vault":
                className = "com.lifeagent.unified.VaultActivity";
                break;
            case "executor.connections":
                className = "com.lifeagent.unified.ConnectionsActivity";
                break;
            default:
                className = "com.lifeagent.unified.GeneralTaskActivity";
                break;
        }
        Intent intent = new Intent();
        intent.setClassName(context.getPackageName(), className);
        intent.putExtra("lifeagent.os.task_id", task.id);
        intent.putExtra("lifeagent.os.command", task.goal);
        return intent;
    }

    static Intent openNearbyPharmacyIntent(Location location) {
        if (location == null) return null;
        String uri = String.format(Locale.US, "geo:%f,%f?q=%s",
                location.getLatitude(), location.getLongitude(), Uri.encode("약국"));
        return new Intent(Intent.ACTION_VIEW, Uri.parse(uri));
    }

    static Intent deviceCredentialIntent(Context context, String title, String description) {
        KeyguardManager manager = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        if (manager == null || !manager.isDeviceSecure()) return null;
        return manager.createConfirmDeviceCredentialIntent(title, description);
    }

    static boolean isPackageInstalled(Context context, String packageName) {
        try {
            context.getPackageManager().getPackageInfo(packageName, 0);
            return true;
        } catch (PackageManager.NameNotFoundException e) {
            return false;
        }
    }

    static boolean isNotificationListenerEnabled(Context context) {
        String enabled = Settings.Secure.getString(
                context.getContentResolver(), "enabled_notification_listeners");
        if (TextUtils.isEmpty(enabled)) return false;
        ComponentName expected = new ComponentName(context, CommercialNotificationListener.class);
        String[] entries = enabled.split(":");
        for (String entry : entries) {
            ComponentName component = ComponentName.unflattenFromString(entry);
            if (expected.equals(component)) return true;
        }
        return false;
    }

    static boolean isAutofillEnabled(Context context) {
        String enabled = Settings.Secure.getString(context.getContentResolver(), "autofill_service");
        if (TextUtils.isEmpty(enabled)) return false;
        ComponentName expected = new ComponentName(context, SafeAutofillService.class);
        ComponentName actual = ComponentName.unflattenFromString(enabled);
        return expected.equals(actual);
    }

    static final class HealthSnapshot {
        boolean encryptedStore;
        boolean deviceSecure;
        boolean notificationPermission;
        boolean notificationListener;
        boolean autofillService;
        boolean coarseLocation;
        boolean monimoInstalled;
        boolean soopInstalled;
        boolean chzzkInstalled;
        boolean rustDeskInstalled;
        int providerConnectionsNeeded;
        final List<String> blockers = new ArrayList<>();

        boolean corePass() {
            return encryptedStore && deviceSecure && notificationPermission;
        }
    }

    static HealthSnapshot health(Context context) {
        HealthSnapshot health = new HealthSnapshot();
        health.encryptedStore = SecureJsonStore.selfTest(context);
        KeyguardManager keyguard = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        health.deviceSecure = keyguard != null && keyguard.isDeviceSecure();
        health.notificationPermission = Build.VERSION.SDK_INT < 33
                || context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED;
        health.notificationListener = isNotificationListenerEnabled(context);
        health.autofillService = isAutofillEnabled(context);
        health.coarseLocation = context.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        health.monimoInstalled = isPackageInstalled(context, PKG_MONIMO);
        health.soopInstalled = isPackageInstalled(context, PKG_SOOP);
        health.chzzkInstalled = isPackageInstalled(context, PKG_CHZZK);
        health.rustDeskInstalled = isPackageInstalled(context, PKG_RUSTDESK);
        health.providerConnectionsNeeded = 4;
        if (!health.encryptedStore) health.blockers.add("암호화 저장소 점검 실패");
        if (!health.deviceSecure) health.blockers.add("화면 잠금이 설정되지 않음");
        if (!health.notificationPermission) health.blockers.add("앱 알림 권한 없음");
        return health;
    }

    static boolean looksSensitive(String text) {
        if (TextUtils.isEmpty(text)) return false;
        return OTP.matcher(text).find() || PASSWORD.matcher(text).find() || CARD.matcher(text).find();
    }

    static String redact(String text) {
        if (text == null) return "";
        String result = OTP.matcher(text).replaceAll("[인증정보 숨김]");
        result = CARD.matcher(result).replaceAll("[결제정보 숨김]");
        result = ACCOUNT.matcher(result).replaceAll("[계좌정보 숨김]");
        result = LONG_NUMBER.matcher(result).replaceAll("[긴 숫자 숨김]");
        return result;
    }

    static String normalize(String value) {
        if (value == null) return "";
        return value.toLowerCase(Locale.ROOT)
                .replaceAll("[\\s\\p{Punct}·ㆍ]+", "")
                .trim();
    }

    static String clipped(String value, int max) {
        String safe = value == null ? "" : value.trim();
        if (safe.length() <= max) return safe;
        return safe.substring(0, Math.max(0, max - 1)) + "…";
    }

    static boolean containsAny(String value, String... needles) {
        if (value == null) return false;
        for (String needle : needles) if (value.contains(needle)) return true;
        return false;
    }

    static boolean isAllowedChannelUrl(String platform, String rawUrl) {
        try {
            Uri uri = Uri.parse(rawUrl);
            if (!"https".equalsIgnoreCase(uri.getScheme())) return false;
            String host = uri.getHost();
            if (host == null) return false;
            host = host.toLowerCase(Locale.ROOT);
            if ("chzzk".equals(platform)) {
                return host.equals("chzzk.naver.com") || host.endsWith(".chzzk.naver.com");
            }
            if ("soop".equals(platform)) {
                return host.equals("sooplive.co.kr") || host.endsWith(".sooplive.co.kr")
                        || host.equals("sooplive.com") || host.endsWith(".sooplive.com");
            }
            return false;
        } catch (RuntimeException e) {
            return false;
        }
    }

    private static StreamRule exactStreamRule(
            SettingsState settings, String packageName, String normalizedText) {
        List<StreamRule> matches = new ArrayList<>();
        String platform = PKG_CHZZK.equals(packageName) ? "chzzk" : "soop";
        for (StreamRule rule : settings.streamRules) {
            if (platform.equals(rule.platform) && normalizedText.contains(normalize(rule.alias))) {
                matches.add(rule);
            }
        }
        return matches.size() == 1 ? matches.get(0) : null;
    }

    private static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            for (byte b : digest) out.append(String.format(Locale.ROOT, "%02x", b));
            return out.toString();
        } catch (Exception impossible) {
            return Integer.toHexString(value.hashCode());
        }
    }

    private static JSONObject cloneJson(JSONObject input) throws StoreException {
        try {
            return new JSONObject(input == null ? "{}" : input.toString());
        } catch (JSONException e) {
            throw new StoreException("json_clone_failed", e);
        }
    }

    private static JSONArray jsonArray(Iterable<String> values) {
        JSONArray array = new JSONArray();
        if (values != null) for (String value : values) array.put(value);
        return array;
    }

    private static void addStrings(Set<String> target, JSONArray array) {
        if (array == null) return;
        for (int i = 0; i < array.length(); i++) {
            String value = array.optString(i, "");
            if (!value.isEmpty()) target.add(value);
        }
    }

    private static void addStrings(List<String> target, JSONArray array) {
        if (array == null) return;
        for (int i = 0; i < array.length(); i++) {
            String value = array.optString(i, "");
            if (!value.isEmpty()) target.add(value);
        }
    }

    private static void readEvents(List<EventRecord> target, JSONArray array) {
        if (array == null) return;
        for (int i = 0; i < array.length(); i++) {
            EventRecord record = EventRecord.from(array.optJSONObject(i));
            if (record != null) target.add(record);
        }
    }

    private static void readTasks(List<TaskRecord> target, JSONArray array) {
        if (array == null) return;
        for (int i = 0; i < array.length(); i++) {
            TaskRecord record = TaskRecord.from(array.optJSONObject(i));
            if (record != null) target.add(record);
        }
    }

    private static void readOpportunities(List<OpportunityRecord> target, JSONArray array) {
        if (array == null) return;
        for (int i = 0; i < array.length(); i++) {
            OpportunityRecord record = OpportunityRecord.from(array.optJSONObject(i));
            if (record != null) target.add(record);
        }
    }

    private static <T> void trim(List<T> list, int max) {
        while (list.size() > max) list.remove(list.size() - 1);
    }

    private static String safe(String value) {
        return value == null ? "" : value;
    }

    private static <E extends Enum<E>> E enumValue(
            Class<E> type, String value, E fallback) {
        try {
            return Enum.valueOf(type, value);
        } catch (Exception ignored) {
            return fallback;
        }
    }
}
