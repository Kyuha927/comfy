package com.lifeagent.unified;

import android.app.Application;

import com.lifeagent.unified.core.AgentRuntime;
import com.lifeagent.unified.services.BenefitScanJobService;

public final class LifeAgentApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        AgentRuntime.get(this);
        BenefitScanJobService.schedule(this);
    }
}
