package com.lifeagent.unified.ui;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Space;
import android.widget.TextView;

public final class Ui {
    public static final int CANVAS = Color.rgb(247, 244, 238);
    public static final int SURFACE = Color.rgb(255, 252, 247);
    public static final int INK = Color.rgb(29, 39, 34);
    public static final int MUTED = Color.rgb(102, 112, 104);
    public static final int SAGE = Color.rgb(112, 136, 121);
    public static final int SAGE_SOFT = Color.rgb(228, 236, 229);
    public static final int TERRA = Color.rgb(181, 111, 85);
    public static final int TERRA_SOFT = Color.rgb(242, 226, 217);
    public static final int AMBER_SOFT = Color.rgb(245, 235, 207);
    public static final int RED_SOFT = Color.rgb(246, 221, 218);
    public static final int DIVIDER = Color.rgb(222, 216, 206);

    private Ui() {}

    public static int dp(Context context, int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }

    public static TextView text(Context context, String value, float sizeSp, boolean bold) {
        TextView view = new TextView(context);
        view.setText(value);
        view.setTextSize(sizeSp);
        view.setTextColor(INK);
        view.setLineSpacing(0f, 1.08f);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    public static TextView title(Context context, String value) {
        TextView view = text(context, value, 25f, true);
        view.setPadding(0, dp(context, 2), 0, dp(context, 2));
        return view;
    }

    public static TextView section(Context context, String value) {
        TextView view = text(context, value, 19f, true);
        view.setPadding(0, dp(context, 24), 0, dp(context, 10));
        return view;
    }

    public static LinearLayout card(Context context) {
        LinearLayout card = new LinearLayout(context);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(context, 16), dp(context, 15), dp(context, 16), dp(context, 15));
        card.setBackground(rounded(SURFACE, 18, DIVIDER, 1, context));
        card.setElevation(dp(context, 1));
        return card;
    }

    public static TextView chip(Context context, String value, int background) {
        TextView chip = text(context, value, 12.5f, true);
        chip.setGravity(Gravity.CENTER);
        chip.setMinHeight(dp(context, 32));
        chip.setPadding(dp(context, 11), dp(context, 5), dp(context, 11), dp(context, 5));
        chip.setBackground(rounded(background, 50, Color.TRANSPARENT, 0, context));
        return chip;
    }

    public static Button primaryButton(Context context, String label) {
        Button button = buttonBase(context, label);
        button.setTextColor(Color.WHITE);
        button.setBackground(rounded(TERRA, 14, TERRA, 0, context));
        return button;
    }

    public static Button secondaryButton(Context context, String label) {
        Button button = buttonBase(context, label);
        button.setTextColor(INK);
        button.setBackground(rounded(SAGE_SOFT, 14, SAGE, 1, context));
        return button;
    }

    public static Button ghostButton(Context context, String label) {
        Button button = buttonBase(context, label);
        button.setTextColor(INK);
        button.setBackground(rounded(SURFACE, 14, DIVIDER, 1, context));
        return button;
    }

    private static Button buttonBase(Context context, String label) {
        Button button = new Button(context);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextSize(14.5f);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setMinHeight(dp(context, 48));
        button.setPadding(dp(context, 14), dp(context, 5), dp(context, 14), dp(context, 5));
        button.setStateListAnimator(null);
        return button;
    }

    public static LinearLayout horizontal(Context context) {
        LinearLayout row = new LinearLayout(context);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        return row;
    }

    public static View divider(Context context) {
        View view = new View(context);
        view.setBackgroundColor(DIVIDER);
        view.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(context, 1)));
        return view;
    }

    public static Space space(Context context, int heightDp) {
        Space space = new Space(context);
        space.setLayoutParams(new LinearLayout.LayoutParams(1, dp(context, heightDp)));
        return space;
    }

    public static ScrollView scrollPage(Context context, LinearLayout body) {
        ScrollView scroll = new ScrollView(context);
        scroll.setFillViewport(true);
        scroll.setClipToPadding(false);
        scroll.addView(body, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return scroll;
    }

    public static LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    public static LinearLayout.LayoutParams weighted() {
        return new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
    }

    public static LinearLayout.LayoutParams withMargins(Context context, int top, int bottom) {
        LinearLayout.LayoutParams params = matchWrap();
        params.topMargin = dp(context, top);
        params.bottomMargin = dp(context, bottom);
        return params;
    }

    public static GradientDrawable rounded(int fill, int radiusDp, int stroke,
                                           int strokeWidthDp, Context context) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setCornerRadius(dp(context, radiusDp));
        if (strokeWidthDp > 0 && stroke != Color.TRANSPARENT) {
            drawable.setStroke(dp(context, strokeWidthDp), stroke);
        }
        return drawable;
    }
}
