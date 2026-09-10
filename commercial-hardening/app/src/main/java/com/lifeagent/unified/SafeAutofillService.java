package com.lifeagent.unified;

import android.app.assist.AssistStructure;
import android.content.ComponentName;
import android.content.Context;
import android.os.CancellationSignal;
import android.service.autofill.AutofillService;
import android.service.autofill.Dataset;
import android.service.autofill.FillCallback;
import android.service.autofill.FillContext;
import android.service.autofill.FillRequest;
import android.service.autofill.FillResponse;
import android.service.autofill.SaveCallback;
import android.service.autofill.SaveRequest;
import android.text.InputType;
import android.text.TextUtils;
import android.view.View;
import android.view.autofill.AutofillId;
import android.view.autofill.AutofillManager;
import android.view.autofill.AutofillValue;
import android.widget.RemoteViews;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Conservative autofill implementation.
 *
 * Only explicit low-risk fields are offered, only in a small browser allowlist, and only when
 * field meaning is unambiguous. Passwords, usernames, OTP, payment and finance surfaces are
 * always excluded. The service never captures values in onSaveRequest.
 */
public final class SafeAutofillService extends AutofillService {
    private static final Set<String> ALLOWED_BROWSER_PACKAGES = Collections.unmodifiableSet(
            new HashSet<>(Arrays.asList(
                    "com.android.chrome",
                    "com.sec.android.app.sbrowser",
                    "org.mozilla.firefox",
                    "com.microsoft.emmx"
            )));

    private static final String[] BLOCKED_PACKAGE_FRAGMENTS = new String[]{
            "bank", "card", "pay", "finance", "wallet", "auth", "security",
            "smcard", "ibk", "kbstar", "woori", "shinhan", "hana", "toss"
    };

    private enum Semantic {
        NAME,
        EMAIL,
        PHONE,
        ADDRESS,
        BLOCKED,
        UNKNOWN
    }

    private static final class Field {
        final AutofillId id;
        final Semantic semantic;
        final int confidence;

        Field(AutofillId id, Semantic semantic, int confidence) {
            this.id = id;
            this.semantic = semantic;
            this.confidence = confidence;
        }
    }

    @Override
    public void onFillRequest(
            FillRequest request,
            CancellationSignal cancellationSignal,
            FillCallback callback) {
        if (request == null || callback == null || cancellationSignal.isCanceled()) {
            if (callback != null) callback.onSuccess(null);
            return;
        }
        try {
            List<FillContext> contexts = request.getFillContexts();
            if (contexts == null || contexts.isEmpty()) {
                callback.onSuccess(null);
                return;
            }
            AssistStructure structure = contexts.get(contexts.size() - 1).getStructure();
            ComponentName component = structure.getActivityComponent();
            String packageName = component == null ? "" : component.getPackageName();
            if (!allowedSurface(packageName)) {
                callback.onSuccess(null);
                return;
            }

            CommercialCore.AppState state = CommercialCore.load(this);
            CommercialCore.ProfileState profile = state.profile;
            List<Field> fields = new ArrayList<>();
            for (int i = 0; i < structure.getWindowNodeCount(); i++) {
                collect(structure.getWindowNodeAt(i).getRootViewNode(), fields, 0);
            }
            if (fields.isEmpty()) {
                callback.onSuccess(null);
                return;
            }

            RemoteViews presentation = new RemoteViews(getPackageName(), android.R.layout.simple_list_item_1);
            presentation.setTextViewText(android.R.id.text1, "Life Agent 안전 자동입력");
            Dataset.Builder dataset = new Dataset.Builder(presentation);
            int filled = 0;
            Set<Semantic> used = new HashSet<>();
            for (Field field : fields) {
                if (field.confidence < 2 || field.semantic == Semantic.BLOCKED
                        || field.semantic == Semantic.UNKNOWN || used.contains(field.semantic)) continue;
                String value = valueFor(profile, field.semantic);
                if (TextUtils.isEmpty(value)) continue;
                dataset.setValue(field.id, AutofillValue.forText(value), presentation);
                used.add(field.semantic);
                filled++;
            }
            if (filled == 0) {
                callback.onSuccess(null);
                return;
            }
            FillResponse response = new FillResponse.Builder().addDataset(dataset.build()).build();
            callback.onSuccess(response);
        } catch (CommercialCore.StoreException | RuntimeException error) {
            callback.onSuccess(null);
        }
    }

    @Override
    public void onSaveRequest(SaveRequest request, SaveCallback callback) {
        // Life Agent never learns or stores values entered into websites.
        if (callback != null) callback.onSuccess();
    }

    private static boolean allowedSurface(String packageName) {
        if (TextUtils.isEmpty(packageName) || !ALLOWED_BROWSER_PACKAGES.contains(packageName)) return false;
        String lower = packageName.toLowerCase(Locale.ROOT);
        for (String fragment : BLOCKED_PACKAGE_FRAGMENTS) {
            if (lower.contains(fragment)) return false;
        }
        return true;
    }

    private static void collect(AssistStructure.ViewNode node, List<Field> fields, int depth) {
        if (node == null || depth > 80 || fields.size() > 80) return;
        AutofillId id = node.getAutofillId();
        if (id != null && node.getAutofillType() == View.AUTOFILL_TYPE_TEXT) {
            Field field = classify(node);
            if (field.semantic != Semantic.UNKNOWN) fields.add(field);
        }
        for (int i = 0; i < node.getChildCount(); i++) {
            collect(node.getChildAt(i), fields, depth + 1);
        }
    }

    private static Field classify(AssistStructure.ViewNode node) {
        String[] hints = node.getAutofillHints();
        String idEntry = lower(node.getIdEntry());
        String hintText = lower(node.getHint());
        String text = lower(node.getText() == null ? "" : node.getText().toString());
        String joined = String.join(" ", idEntry, hintText, text, joinHints(hints));
        int inputType = node.getInputType();

        if (isPasswordInput(inputType)
                || containsAny(joined, "password", "passwd", "비밀번호", "pin", "otp", "인증번호",
                "creditcard", "cardnumber", "cvv", "cvc", "계좌", "주민", "socialsecurity",
                "username", "userid", "loginid")) {
            return new Field(node.getAutofillId(), Semantic.BLOCKED, 3);
        }

        Semantic hinted = fromHints(hints);
        if (hinted != Semantic.UNKNOWN) return new Field(node.getAutofillId(), hinted, 3);

        if (exactAny(idEntry, "email", "emailaddress", "useremail")
                || exactAny(hintText, "이메일", "이메일주소", "email")) {
            return new Field(node.getAutofillId(), Semantic.EMAIL, 2);
        }
        if (exactAny(idEntry, "phone", "phonenumber", "mobile", "tel")
                || exactAny(hintText, "전화번호", "휴대폰번호", "연락처", "phone")) {
            return new Field(node.getAutofillId(), Semantic.PHONE, 2);
        }
        if (exactAny(idEntry, "fullname", "realname", "name")
                || exactAny(hintText, "이름", "성명", "name")) {
            return new Field(node.getAutofillId(), Semantic.NAME, 2);
        }
        if (exactAny(idEntry, "address", "streetaddress", "postaladdress")
                || exactAny(hintText, "주소", "도로명주소", "address")) {
            return new Field(node.getAutofillId(), Semantic.ADDRESS, 2);
        }
        return new Field(node.getAutofillId(), Semantic.UNKNOWN, 0);
    }

    private static Semantic fromHints(String[] hints) {
        if (hints == null) return Semantic.UNKNOWN;
        for (String hint : hints) {
            String value = lower(hint);
            if (containsAny(value, "password", "username", "creditcard", "otp", "smsotp")) {
                return Semantic.BLOCKED;
            }
            if (AutofillManager.AUTOFILL_HINT_EMAIL_ADDRESS.equals(hint)) return Semantic.EMAIL;
            if (AutofillManager.AUTOFILL_HINT_PHONE_NUMBER.equals(hint)) return Semantic.PHONE;
            if (AutofillManager.AUTOFILL_HINT_NAME.equals(hint)) return Semantic.NAME;
            if (AutofillManager.AUTOFILL_HINT_POSTAL_ADDRESS.equals(hint)
                    || AutofillManager.AUTOFILL_HINT_POSTAL_CODE.equals(hint)) return Semantic.ADDRESS;
        }
        return Semantic.UNKNOWN;
    }

    private static String valueFor(CommercialCore.ProfileState profile, Semantic semantic) {
        switch (semantic) {
            case NAME: return profile.displayName;
            case EMAIL: return profile.email;
            case PHONE: return profile.phone;
            case ADDRESS: return profile.address;
            default: return "";
        }
    }

    private static boolean isPasswordInput(int inputType) {
        int variation = inputType & InputType.TYPE_MASK_VARIATION;
        return variation == InputType.TYPE_TEXT_VARIATION_PASSWORD
                || variation == InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                || variation == InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD
                || variation == InputType.TYPE_NUMBER_VARIATION_PASSWORD;
    }

    private static String joinHints(String[] hints) {
        if (hints == null || hints.length == 0) return "";
        return String.join(" ", hints).toLowerCase(Locale.ROOT);
    }

    private static String lower(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private static boolean exactAny(String value, String... options) {
        for (String option : options) if (option.equals(value)) return true;
        return false;
    }

    private static boolean containsAny(String value, String... options) {
        for (String option : options) if (value.contains(option)) return true;
        return false;
    }
}
