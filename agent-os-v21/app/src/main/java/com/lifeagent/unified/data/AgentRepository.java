package com.lifeagent.unified.data;

import android.content.Context;
import android.content.SharedPreferences;

import com.lifeagent.unified.core.AgentCore;
import com.lifeagent.unified.security.SecureVault;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Persistent, encrypted repository for context facts, task graphs, events and recipes. */
public final class AgentRepository {
    private static final String SETTINGS = "life_agent_os_settings_v21";
    private static final String KEY_FACTS = "context.facts";
    private static final String KEY_TASKS = "tasks.graphs";
    private static final String KEY_EVENTS = "events.sanitized";
    private static final String KEY_RECIPES = "recipes.graphs";
    private static final int MAX_EVENTS = 50;
    private static final int MAX_TASKS = 100;
    private static final long EVENT_TTL_MS = 7L * 24 * 60 * 60 * 1000;

    private final SecureVault vault;
    private final SharedPreferences settings;

    public AgentRepository(Context context) {
        Context app = context.getApplicationContext();
        this.vault = SecureVault.get(app);
        this.settings = app.getSharedPreferences(SETTINGS, Context.MODE_PRIVATE);
        ensureDefaultRecipes();
    }

    public static final class StoredTask {
        public final String id;
        public final String goal;
        public final String skillId;
        public final String skillName;
        public final AgentCore.TaskStatus status;
        public final int activeNodeIndex;
        public final String nextAction;
        public final String completionEvidence;
        public final long createdAt;
        public final long updatedAt;
        public final List<StoredNode> nodes;

        StoredTask(String id, String goal, String skillId, String skillName,
                   AgentCore.TaskStatus status, int activeNodeIndex, String nextAction,
                   String completionEvidence, long createdAt, long updatedAt,
                   List<StoredNode> nodes) {
            this.id = id;
            this.goal = goal;
            this.skillId = skillId;
            this.skillName = skillName;
            this.status = status;
            this.activeNodeIndex = activeNodeIndex;
            this.nextAction = nextAction;
            this.completionEvidence = completionEvidence;
            this.createdAt = createdAt;
            this.updatedAt = updatedAt;
            this.nodes = Collections.unmodifiableList(new ArrayList<>(nodes));
        }
    }

    public static final class StoredNode {
        public final String id;
        public final String title;
        public final AgentCore.TaskStatus status;
        public final AgentCore.ExecutorType executor;
        public final AgentCore.PolicyDecision policy;
        public final String verification;
        public final String evidence;
        public final String failureCode;

        StoredNode(String id, String title, AgentCore.TaskStatus status,
                   AgentCore.ExecutorType executor, AgentCore.PolicyDecision policy,
                   String verification, String evidence, String failureCode) {
            this.id = id;
            this.title = title;
            this.status = status;
            this.executor = executor;
            this.policy = policy;
            this.verification = verification;
            this.evidence = evidence;
            this.failureCode = failureCode;
        }
    }

    public synchronized void putFact(AgentCore.ContextFact fact) {
        JSONObject root = readObject(KEY_FACTS);
        try {
            JSONObject item = new JSONObject();
            item.put("key", fact.key);
            item.put("value", fact.value);
            item.put("sensitivity", fact.sensitivity.name());
            item.put("expires", fact.expiresAtEpochMs);
            item.put("automation", fact.mayDriveAutomation);
            item.put("commercial", fact.mayDriveCommercialRecommendations);
            root.put(fact.key, item);
            writeObject(KEY_FACTS, root);
        } catch (JSONException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    public synchronized void removeFact(String key) {
        JSONObject root = readObject(KEY_FACTS);
        root.remove(key);
        writeObject(KEY_FACTS, root);
    }

    public synchronized AgentCore.PersonalContextGraph loadContextGraph(long nowEpochMs) {
        AgentCore.PersonalContextGraph graph = new AgentCore.PersonalContextGraph();
        JSONObject root = readObject(KEY_FACTS);
        List<String> expired = new ArrayList<>();
        for (java.util.Iterator<String> it = root.keys(); it.hasNext();) {
            String key = it.next();
            JSONObject item = root.optJSONObject(key);
            if (item == null) continue;
            long expires = item.optLong("expires", 0L);
            if (expires > 0 && nowEpochMs >= expires) {
                expired.add(key);
                continue;
            }
            graph.put(new AgentCore.ContextFact(
                    key,
                    item.optString("value", ""),
                    enumOr(AgentCore.Sensitivity.class, item.optString("sensitivity"), AgentCore.Sensitivity.PERSONAL),
                    expires,
                    item.optBoolean("automation", false),
                    item.optBoolean("commercial", false)
            ));
        }
        if (!expired.isEmpty()) {
            for (String key : expired) root.remove(key);
            writeObject(KEY_FACTS, root);
        }
        return graph;
    }

    public synchronized String createTask(AgentCore.ActionPlan plan, long nowEpochMs) {
        JSONArray tasks = readArray(KEY_TASKS);
        JSONObject task = new JSONObject();
        try {
            task.put("id", plan.id);
            task.put("goal", plan.goal);
            task.put("skillId", plan.primarySkill.id);
            task.put("skillName", plan.primarySkill.name);
            task.put("status", plan.policy == AgentCore.PolicyDecision.AUTO
                    ? AgentCore.TaskStatus.READY.name() : AgentCore.TaskStatus.WAITING_USER.name());
            task.put("activeNode", 0);
            task.put("nextAction", plan.steps.isEmpty() ? "실행 단계 없음" : plan.steps.get(0).title);
            task.put("completionEvidence", plan.completionEvidence);
            task.put("createdAt", nowEpochMs);
            task.put("updatedAt", nowEpochMs);
            JSONArray nodes = new JSONArray();
            for (AgentCore.PlanStep step : plan.steps) {
                JSONObject node = new JSONObject();
                node.put("id", step.id);
                node.put("title", step.title);
                node.put("status", AgentCore.TaskStatus.PLANNED.name());
                node.put("executor", step.executor.name());
                node.put("policy", step.policy.name());
                node.put("verification", step.verification);
                node.put("evidence", "");
                node.put("failureCode", "");
                nodes.put(node);
            }
            task.put("nodes", nodes);
            JSONArray updated = new JSONArray();
            updated.put(task);
            for (int i = 0; i < tasks.length() && updated.length() < MAX_TASKS; i++) updated.put(tasks.get(i));
            writeArray(KEY_TASKS, updated);
            return plan.id;
        } catch (JSONException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    public synchronized List<StoredTask> listTasks() {
        JSONArray tasks = readArray(KEY_TASKS);
        List<StoredTask> out = new ArrayList<>();
        for (int i = 0; i < tasks.length(); i++) {
            JSONObject task = tasks.optJSONObject(i);
            if (task == null) continue;
            List<StoredNode> nodes = new ArrayList<>();
            JSONArray nodeArray = task.optJSONArray("nodes");
            if (nodeArray != null) {
                for (int j = 0; j < nodeArray.length(); j++) {
                    JSONObject node = nodeArray.optJSONObject(j);
                    if (node == null) continue;
                    nodes.add(new StoredNode(
                            node.optString("id", "node-" + j),
                            node.optString("title", "단계"),
                            enumOr(AgentCore.TaskStatus.class, node.optString("status"), AgentCore.TaskStatus.PLANNED),
                            enumOr(AgentCore.ExecutorType.class, node.optString("executor"), AgentCore.ExecutorType.HUMAN),
                            enumOr(AgentCore.PolicyDecision.class, node.optString("policy"), AgentCore.PolicyDecision.CONFIRM),
                            node.optString("verification", "완료 증거"),
                            node.optString("evidence", ""),
                            node.optString("failureCode", "")
                    ));
                }
            }
            out.add(new StoredTask(
                    task.optString("id", "task-" + i),
                    task.optString("goal", "업무"),
                    task.optString("skillId", "general.delegate"),
                    task.optString("skillName", "일반 업무 위임"),
                    enumOr(AgentCore.TaskStatus.class, task.optString("status"), AgentCore.TaskStatus.PLANNED),
                    task.optInt("activeNode", 0),
                    task.optString("nextAction", "계획 확인"),
                    task.optString("completionEvidence", "완료 증거"),
                    task.optLong("createdAt", 0L),
                    task.optLong("updatedAt", 0L),
                    nodes
            ));
        }
        return Collections.unmodifiableList(out);
    }

    public synchronized boolean updateTaskState(String id, AgentCore.TaskStatus status,
                                                String nextAction, String evidence, String failureCode,
                                                long nowEpochMs) {
        JSONArray tasks = readArray(KEY_TASKS);
        boolean found = false;
        for (int i = 0; i < tasks.length(); i++) {
            JSONObject task = tasks.optJSONObject(i);
            if (task == null || !id.equals(task.optString("id"))) continue;
            found = true;
            try {
                task.put("status", status.name());
                task.put("nextAction", nextAction == null ? "" : nextAction);
                task.put("updatedAt", nowEpochMs);
                int active = task.optInt("activeNode", 0);
                JSONArray nodes = task.optJSONArray("nodes");
                if (nodes != null && active >= 0 && active < nodes.length()) {
                    JSONObject node = nodes.optJSONObject(active);
                    if (node != null) {
                        node.put("status", status.name());
                        if (evidence != null) node.put("evidence", evidence);
                        if (failureCode != null) node.put("failureCode", failureCode);
                    }
                }
            } catch (JSONException impossible) {
                throw new IllegalStateException(impossible);
            }
            break;
        }
        if (found) writeArray(KEY_TASKS, tasks);
        return found;
    }

    public synchronized boolean advanceTask(String id, String evidence, long nowEpochMs) {
        JSONArray tasks = readArray(KEY_TASKS);
        boolean found = false;
        for (int i = 0; i < tasks.length(); i++) {
            JSONObject task = tasks.optJSONObject(i);
            if (task == null || !id.equals(task.optString("id"))) continue;
            found = true;
            int active = task.optInt("activeNode", 0);
            JSONArray nodes = task.optJSONArray("nodes");
            try {
                if (nodes == null || active >= nodes.length()) {
                    task.put("status", evidence == null || evidence.isBlank()
                            ? AgentCore.TaskStatus.VERIFYING.name() : AgentCore.TaskStatus.COMPLETED.name());
                    task.put("nextAction", evidence == null || evidence.isBlank() ? "완료 증거 확인" : "완료");
                } else {
                    JSONObject node = nodes.optJSONObject(active);
                    if (node != null) {
                        node.put("status", AgentCore.TaskStatus.COMPLETED.name());
                        node.put("evidence", evidence == null ? "" : evidence);
                    }
                    active++;
                    task.put("activeNode", active);
                    if (active >= nodes.length()) {
                        task.put("status", evidence == null || evidence.isBlank()
                                ? AgentCore.TaskStatus.VERIFYING.name() : AgentCore.TaskStatus.COMPLETED.name());
                        task.put("nextAction", evidence == null || evidence.isBlank() ? "완료 증거 확인" : "완료");
                    } else {
                        JSONObject next = nodes.optJSONObject(active);
                        task.put("status", AgentCore.TaskStatus.READY.name());
                        task.put("nextAction", next == null ? "다음 단계" : next.optString("title", "다음 단계"));
                    }
                }
                task.put("updatedAt", nowEpochMs);
            } catch (JSONException impossible) {
                throw new IllegalStateException(impossible);
            }
            break;
        }
        if (found) writeArray(KEY_TASKS, tasks);
        return found;
    }

    public synchronized void recordEvent(AgentCore.AmbientEvent event, long nowEpochMs) {
        JSONArray current = readArray(KEY_EVENTS);
        JSONArray updated = new JSONArray();
        try {
            updated.put(eventToJson(event));
            for (int i = 0; i < current.length() && updated.length() < MAX_EVENTS; i++) {
                JSONObject item = current.optJSONObject(i);
                if (item == null) continue;
                long occurred = item.optLong("occurredAt", 0L);
                if (occurred > 0 && nowEpochMs - occurred <= EVENT_TTL_MS) updated.put(item);
            }
            writeArray(KEY_EVENTS, updated);
        } catch (JSONException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    public synchronized AgentCore.AmbientEvent latestEvent(long nowEpochMs) {
        JSONArray events = readArray(KEY_EVENTS);
        for (int i = 0; i < events.length(); i++) {
            JSONObject item = events.optJSONObject(i);
            if (item == null) continue;
            long occurred = item.optLong("occurredAt", 0L);
            if (occurred > 0 && nowEpochMs - occurred > EVENT_TTL_MS) continue;
            return eventFromJson(item);
        }
        return null;
    }

    public synchronized List<AgentCore.Recipe> listRecipes() {
        JSONArray recipes = readArray(KEY_RECIPES);
        List<AgentCore.Recipe> out = new ArrayList<>();
        for (int i = 0; i < recipes.length(); i++) {
            JSONObject item = recipes.optJSONObject(i);
            if (item == null) continue;
            Map<String, String> conditions = new LinkedHashMap<>();
            JSONObject conditionJson = item.optJSONObject("conditions");
            if (conditionJson != null) {
                for (java.util.Iterator<String> it = conditionJson.keys(); it.hasNext();) {
                    String key = it.next();
                    conditions.put(key, conditionJson.optString(key, ""));
                }
            }
            out.add(new AgentCore.Recipe(
                    item.optString("id", "recipe-" + i),
                    item.optString("name", "자동화"),
                    item.optString("triggerType", "goal"),
                    conditions,
                    item.optString("skillId", "general.delegate"),
                    enumOr(AgentCore.PolicyDecision.class, item.optString("maximumAutomation"), AgentCore.PolicyDecision.CONFIRM),
                    item.optString("verification", "완료 증거"),
                    item.optBoolean("enabled", true)
            ));
        }
        return Collections.unmodifiableList(out);
    }

    public synchronized void saveRecipe(AgentCore.Recipe recipe) {
        JSONArray current = readArray(KEY_RECIPES);
        JSONArray updated = new JSONArray();
        try {
            updated.put(recipeToJson(recipe));
            for (int i = 0; i < current.length(); i++) {
                JSONObject existing = current.optJSONObject(i);
                if (existing == null || recipe.id.equals(existing.optString("id"))) continue;
                updated.put(existing);
            }
            writeArray(KEY_RECIPES, updated);
        } catch (JSONException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    public void setPlainSetting(String key, boolean value) {
        settings.edit().putBoolean(key, value).apply();
    }

    public boolean getPlainSetting(String key, boolean fallback) {
        return settings.getBoolean(key, fallback);
    }

    public void setPlainString(String key, String value) {
        settings.edit().putString(key, value == null ? "" : value).apply();
    }

    public String getPlainString(String key, String fallback) {
        return settings.getString(key, fallback);
    }

    public synchronized void wipeAll() {
        vault.clearAll();
        settings.edit().clear().commit();
        ensureDefaultRecipes();
    }

    private void ensureDefaultRecipes() {
        if (vault.contains(KEY_RECIPES)) return;
        saveRecipe(new AgentCore.Recipe("insurance-followup", "보험 추가서류 후속 처리",
                "notification.insurance_followup", Map.of(), "insurance.monimo.claim",
                AgentCore.PolicyDecision.CONFIRM, "추가서류 접수 확인", true));
        saveRecipe(new AgentCore.Recipe("benefit-alert", "혜택 안내 자격 확인",
                "notification.benefit", Map.of(), "benefits.autopilot",
                AgentCore.PolicyDecision.AUTO, "자격 대조 결과", true));
        saveRecipe(new AgentCore.Recipe("stream-live", "선택 방송 자동 실행",
                "notification.stream_live", Map.of(), "stream.autoplay",
                AgentCore.PolicyDecision.AUTO, "대상 채널 식별", false));
    }

    private JSONObject readObject(String key) {
        String raw = vault.get(key);
        if (raw.isBlank()) return new JSONObject();
        try {
            return new JSONObject(raw);
        } catch (JSONException error) {
            throw new SecurityException("암호화 저장소의 JSON이 손상되었습니다.", error);
        }
    }

    private JSONArray readArray(String key) {
        String raw = vault.get(key);
        if (raw.isBlank()) return new JSONArray();
        try {
            return new JSONArray(raw);
        } catch (JSONException error) {
            throw new SecurityException("암호화 저장소의 배열이 손상되었습니다.", error);
        }
    }

    private void writeObject(String key, JSONObject value) {
        vault.put(key, value.toString());
    }

    private void writeArray(String key, JSONArray value) {
        vault.put(key, value.toString());
    }

    private static JSONObject eventToJson(AgentCore.AmbientEvent event) throws JSONException {
        JSONObject item = new JSONObject();
        item.put("id", event.id);
        item.put("source", event.source);
        item.put("type", event.type);
        item.put("summary", event.summary);
        item.put("package", event.packageName);
        item.put("occurredAt", event.occurredAtEpochMs);
        item.put("sensitivity", event.sensitivity.name());
        item.put("actionable", event.actionable);
        JSONObject entities = new JSONObject();
        for (Map.Entry<String, String> entry : event.entities.entrySet()) {
            entities.put(entry.getKey(), AgentCore.sanitizeIncoming(entry.getValue()));
        }
        item.put("entities", entities);
        return item;
    }

    private static AgentCore.AmbientEvent eventFromJson(JSONObject item) {
        Map<String, String> entities = new LinkedHashMap<>();
        JSONObject entityJson = item.optJSONObject("entities");
        if (entityJson != null) {
            for (java.util.Iterator<String> it = entityJson.keys(); it.hasNext();) {
                String key = it.next();
                entities.put(key, entityJson.optString(key, ""));
            }
        }
        return new AgentCore.AmbientEvent(
                item.optString("id", ""),
                item.optString("source", "notification"),
                item.optString("type", "notification.other"),
                item.optString("summary", ""),
                item.optString("package", ""),
                item.optLong("occurredAt", 0L),
                entities,
                enumOr(AgentCore.Sensitivity.class, item.optString("sensitivity"), AgentCore.Sensitivity.PERSONAL),
                item.optBoolean("actionable", false)
        );
    }

    private static JSONObject recipeToJson(AgentCore.Recipe recipe) throws JSONException {
        JSONObject item = new JSONObject();
        item.put("id", recipe.id);
        item.put("name", recipe.name);
        item.put("triggerType", recipe.triggerType);
        JSONObject conditions = new JSONObject();
        for (Map.Entry<String, String> entry : recipe.conditions.entrySet()) {
            conditions.put(entry.getKey(), entry.getValue());
        }
        item.put("conditions", conditions);
        item.put("skillId", recipe.skillId);
        item.put("maximumAutomation", recipe.maximumAutomation.name());
        item.put("verification", recipe.verification);
        item.put("enabled", recipe.enabled);
        return item;
    }

    private static <T extends Enum<T>> T enumOr(Class<T> type, String raw, T fallback) {
        if (raw == null || raw.isBlank()) return fallback;
        try {
            return Enum.valueOf(type, raw);
        } catch (IllegalArgumentException ignored) {
            return fallback;
        }
    }
}
