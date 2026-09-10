package com.lifeagent.unified;

import android.test.ActivityInstrumentationTestCase2;

public final class MainActivitySmokeTest extends ActivityInstrumentationTestCase2<MainActivity> {
    public MainActivitySmokeTest() {
        super(MainActivity.class);
    }

    public void testMainActivityLaunchesAndRenders() {
        MainActivity activity = getActivity();
        assertNotNull(activity);
        assertNotNull(activity.getWindow());
        assertNotNull(activity.findViewById(android.R.id.content));
        assertTrue(activity.findViewById(android.R.id.content).isShown());
    }
}
