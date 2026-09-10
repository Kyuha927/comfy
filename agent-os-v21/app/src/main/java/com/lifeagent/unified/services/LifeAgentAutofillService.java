package com.lifeagent.unified.services;

import android.app.assist.AssistStructure;
import android.os.CancellationSignal;
import android.service.autofill.AutofillService;
import android.service.autofill.Dataset;
import android.service.autofill.FillCallback;
import android.service.autofill.FillContext;
import android.service.autofill.FillRequest;
import android.service.autofill.FillResponse;
import android.service.autofill.SaveCallback;
import android.service.autofill.SaveRequest;
import android.view.autofill.AutofillId;
import android.view.autofill.AutofillValue;
import android.widget.RemoteViews;

import com.lifeagent.unified.core.AgentCore;
import com.lifeagent.unified.core.AgentRuntime;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Fills only identity/contact fields. Password, OTP and payment fields are always excluded. */
public final class LifeAgentAutofillService extends AutofillService {
    @Override
    public void onFillRequest(FillRequest request, CancellationSignal cancellationSignal,
                              FillCallback callback) {
        try {
            List<FillContext> contexts = request.getFillContexts();
            if (contexts == null || contexts.isEmpty()) {
                callback.onSuccess(null);
                return;
            }
            AssistStructure structure = contexts.get(contexts.size() - 1).getStructure();
            List<Field> fields = new ArrayList<>();
            for (int i = 0; i < structure.getWindowNodeCount(); i++) {
                collect(structure.getWindowNodeAt(i).getRootViewNode(), fields);
            }
            if (fields.isEmpty()) {
                callback.onSuccess(null);
                return;
            }

            long now = AgentCore.now();
            AgentCore.PersonalContextGraph graph = AgentRuntime.get(this).repository().loadContextGraph(now);
            Dataset.Builder dataset = new Dataset.Builder();
            int filled = 0;
            for (Field field : fields) {
                String value = valueFor(field.semantic, graph, now);
                if (value.isBlank()) continue;
                RemoteViews presentation = new RemoteViews(getPackageName(), android.R.layout.simple_list_item_1);
                presentation.setTextViewText(android.R.id.text1, "Life Agent · " + labelFor(field.semantic));
                dataset.setValue(field.id, AutofillValue.forText(value), presentation);
                filled++;
            }
            if (filled == 0) {
                callback.onSuccess(null);
                return;
            }
            RemoteViews responsePresentation = new RemoteViews(getPackageName(), android.R.layout.simple_list_item_1);
            responsePresentation.setTextViewText(android.R.id.text1, "Life Agent 개인정보 금고");
            dataset.setPresentation(responsePresentation);
            FillResponse response = new FillResponse.Builder().addDataset(dataset.build()).build();
            callback.onSuccess(response);
        } catch (RuntimeException error) {
            callback.onFailure("자동입력 구조를 안전하게 확인하지 못했습니다.");
        }
    }

    @Override
    public void onSaveRequest(SaveRequest request, SaveCallback callback) {
        // Never learn passwords or arbitrary form contents from third-party apps.
        callback.onSuccess();
    }

    private void collect(AssistStructure.ViewNode node, List<Field> out) {
        if (node == null) return;
        AutofillId id = node.getAutofillId();
        if (id != null) {
            String descriptor = descriptor(node);
            Semantic semantic = classify(descriptor, node.getAutofillHints());
            if (semantic != Semantic.NONE && semantic != Semantic.FORBIDDEN) {
                out.add(new Field(id, semantic));
            }
        }
        for (int i = 0; i < node.getChildCount(); i++) collect(node.getChildAt(i), out);
    }

    private String descriptor(AssistStructure.ViewNode node) {
        StringBuilder builder = new StringBuilder();
        append(builder, node.getIdEntry());
        append(builder, node.getHint());
        append(builder, node.getText());
        append(builder, node.getContentDescription());
        return AgentCore.normalize(builder.toString());
    }

    private void append(StringBuilder builder, CharSequence value) {
        if (value != null) builder.append(value).append(' ');
    }

    private Semantic classify(String descriptor, String[] hints) {
        StringBuilder combined = new StringBuilder(descriptor);
        if (hints != null) for (String hint : hints) combined.append(AgentCore.normalize(hint));
        String text = combined.toString();
        if (containsAny(text, "password", "비밀번호", "otp", "인증번호", "verificationcode",
                "creditcard", "cardnumber", "cvv", "cvc", "pin", "보안카드", "계좌")) {
            return Semantic.FORBIDDEN;
        }
        if (containsAny(text, "email", "이메일", "mailaddress")) return Semantic.EMAIL;
        if (containsAny(text, "phone", "tel", "mobile", "전화번호", "휴대폰")) return Semantic.PHONE;
        if (containsAny(text, "postal", "zipcode", "우편번호")) return Semantic.POSTAL;
        if (containsAny(text, "address", "street", "주소")) return Semantic.ADDRESS;
        if (containsAny(text, "personname", "fullname", "name", "성명", "이름")
                && !containsAny(text, "username", "nickname", "아이디", "닉네임")) return Semantic.NAME;
        return Semantic.NONE;
    }

    private String valueFor(Semantic semantic, AgentCore.PersonalContextGraph graph, long now) {
        switch (semantic) {
            case NAME: return graph.value("profile.name", now);
            case EMAIL: return graph.value("profile.email", now);
            case PHONE: return graph.value("profile.phone", now);
            case ADDRESS: return graph.value("profile.address", now);
            case POSTAL: return graph.value("profile.postal", now);
            default: return "";
        }
    }

    private String labelFor(Semantic semantic) {
        switch (semantic) {
            case NAME: return "이름";
            case EMAIL: return "이메일";
            case PHONE: return "전화번호";
            case ADDRESS: return "주소";
            case POSTAL: return "우편번호";
            default: return "개인정보";
        }
    }

    private boolean containsAny(String text, String... tokens) {
        for (String token : tokens) if (text.contains(AgentCore.normalize(token))) return true;
        return false;
    }

    private enum Semantic { NONE, FORBIDDEN, NAME, EMAIL, PHONE, ADDRESS, POSTAL }

    private static final class Field {
        final AutofillId id;
        final Semantic semantic;

        Field(AutofillId id, Semantic semantic) {
            this.id = id;
            this.semantic = semantic;
        }
    }
}
