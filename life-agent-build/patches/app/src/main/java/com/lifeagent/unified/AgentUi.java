package com.lifeagent.unified;

import android.content.Context;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Compact design system for the Agent OS shell. */
final class AgentUi {
    static final int CANVAS = 0xfff7f4ed;
    static final int SURFACE = 0xffffffff;
    static final int SURFACE_ALT = 0xffefede6;
    static final int INK = 0xff20231f;
    static final int INK_SOFT = 0xff626861;
    static final int LINE = 0xffdcdad2;
    static final int SAGE = 0xff78907b;
    static final int SAGE_DARK = 0xff435f49;
    static final int SAGE_PALE = 0xffe6eee6;
    static final int TERRA = 0xffb9684f;
    static final int TERRA_PALE = 0xfff4e6df;
    static final int WARNING = 0xff8a5a24;
    static final int WARNING_PALE = 0xfffff0d7;
    static final int DANGER = 0xff9a403d;
    static final int DANGER_PALE = 0xffffe8e5;

    private AgentUi() {}

    static int dp(Context c, int value) {
        return Math.round(value * c.getResources().getDisplayMetrics().density);
    }

    static TextView text(Context c, String value, int sp, boolean bold, int color) {
        TextView v = new TextView(c);
        v.setText(value == null ? "" : value);
        v.setTextSize(sp);
        v.setTextColor(color);
        v.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        if (bold) v.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return v;
    }

    static TextView pill(Context c, String value, int background, int foreground) {
        TextView v = text(c, value, 12, true, foreground);
        v.setGravity(Gravity.CENTER);
        v.setPadding(dp(c, 10), dp(c, 5), dp(c, 10), dp(c, 5));
        v.setBackground(round(background, 999, 0, 0));
        return v;
    }

    static LinearLayout card(Context c, View child, int background) {
        LinearLayout box = new LinearLayout(c);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(c, 16), dp(c, 16), dp(c, 16), dp(c, 16));
        box.setBackground(round(background, 22, LINE, 1));
        box.setElevation(dp(c, 1));
        box.addView(child, matchWrap());
        return box;
    }

    static Button primary(Context c, String label, View.OnClickListener listener) {
        Button b = new Button(c);
        b.setAllCaps(false);
        b.setText(label);
        b.setTextSize(15);
        b.setTextColor(0xffffffff);
        b.setGravity(Gravity.CENTER);
        b.setMinHeight(dp(c, 48));
        b.setPadding(dp(c, 14), dp(c, 10), dp(c, 14), dp(c, 10));
        b.setBackground(round(SAGE_DARK, 16, 0, 0));
        b.setOnClickListener(listener);
        return b;
    }

    static Button secondary(Context c, String label, View.OnClickListener listener) {
        Button b = new Button(c);
        b.setAllCaps(false);
        b.setText(label);
        b.setTextSize(14);
        b.setTextColor(INK);
        b.setGravity(Gravity.CENTER);
        b.setMinHeight(dp(c, 44));
        b.setPadding(dp(c, 12), dp(c, 9), dp(c, 12), dp(c, 9));
        b.setBackground(round(SURFACE, 14, LINE, 1));
        b.setOnClickListener(listener);
        return b;
    }

    static GradientDrawable round(int color, int radius, int strokeColor, int strokeWidth) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(radius * 2f);
        if (strokeWidth > 0) d.setStroke(strokeWidth, strokeColor);
        return d;
    }

    static LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    static LinearLayout.LayoutParams wrapWrap() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    static LinearLayout.LayoutParams spaced(Context c, int top, int bottom) {
        LinearLayout.LayoutParams p = matchWrap();
        p.topMargin = dp(c, top);
        p.bottomMargin = dp(c, bottom);
        return p;
    }
}
