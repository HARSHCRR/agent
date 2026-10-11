#pragma once

#include <future>
#include <iostream>
#include <sstream>
#include <string>

#include "config.hpp"
#include "http_client.hpp"
#include "models.hpp"

namespace analysts {

inline const std::string ANALYST_PROMPT_TEMPLATE = 
R"(You are an institutional quantitative equity analyst assigned to argue the %SIDE% case for NAS100 (Nasdaq 100) for today's US cash session. You will be given a briefing pack.

Rules:
- Use ONLY information in the briefing pack. Do not use outside knowledge of market events, prices, or news. If something is not in the pack, do not claim it.
- Every key driver must cite evidence IDs from the pack (E1, Y1, H3, or PRICE).
- Argue the %SIDE% case as strongly as the evidence honestly allows. Do not invent or exaggerate support. If the evidence for your side is weak, say so in data_gaps instead of padding.
- Also state the single strongest point against your own case.
- Do not give trade advice, entries, stops, targets, or price predictions.
- Check [DATA_STATUS]. If a source failed, list it in data_gaps.
- Output JSON only, matching this exact schema:
{
  "side": "%SIDE%",
  "headline": "string, max 20 words",
  "key_drivers": [
    {"point": "string", "evidence_ids": ["E1"], "horizon": "us_session"}
  ],
  "strongest_counterpoint": "string",
  "invalidation": "string",
  "data_gaps": ["string"]
}
Require exactly 3 key_drivers.
)";

inline CaseOutput generate_mock_case(const std::string& side, const BriefingPack& pack) {
    CaseOutput out;
    out.side = side;

    auto valid_ids = pack.get_valid_evidence_ids();
    std::string first_event = valid_ids.count("E1") ? "E1" : "PRICE";
    std::string first_headline = valid_ids.count("H1") ? "H1" : "PRICE";

    if (side == "BULL") {
        out.headline = "Macro stability and supportive technical structure favor tech continuation into cash open";
        out.key_drivers = {
            {"Nasdaq consolidates near recent highs with VIX contained at 15.31", {"PRICE"}, "us_session"},
            {"Scheduled morning economic releases offer favorable risk-reward for rate expectations", {first_event}, "premarket"},
            {"Early news cycle reflects positive sentiment across semiconductor and tech megacaps", {first_headline}, "multi_day"}
        };
        out.strongest_counterpoint = "Elevated 10-year Treasury yields at 5.28% remain a drag on tech multiples.";
        out.invalidation = "A breakdown below yesterday's low on high morning selling volume.";
        out.data_gaps = pack.failed_sources.empty() ? std::vector<std::string>{"None"} : pack.failed_sources;
    } else {
        out.headline = "Elevated bond yields and upcoming catalyst uncertainty create downside asymmetry for tech";
        out.key_drivers = {
            {"US 10-Year yield pressure at 5.28% caps valuation expansion for Nasdaq 100", {"PRICE"}, "us_session"},
            {"Morning macro prints carry high headline risk with asymmetric downside on sticky figures", {first_event}, "premarket"},
            {"Thin pre-market volume highlights buyer hesitation ahead of scheduled FOMC commentary", {"PRICE"}, "premarket"}
        };
        out.strongest_counterpoint = "VIX drop reflects calm options pricing without aggressive put buying.";
        out.invalidation = "Strong breakout above yesterday's high with expanding upside volume.";
        out.data_gaps = pack.failed_sources.empty() ? std::vector<std::string>{"None"} : pack.failed_sources;
    }
    return out;
}

inline CaseOutput generate_case(const std::string& side, const BriefingPack& pack) {
    if (config::GEMINI_API_KEY.empty() || config::GEMINI_API_KEY == "your_gemini_api_key_here") {
        return generate_mock_case(side, pack);
    }

    // Prepare Gemini REST Request
    std::string url = "https://generativelanguage.googleapis.com/v1beta/models/" + 
                      config::GEMINI_MODEL + ":generateContent?key=" + config::GEMINI_API_KEY;

    std::string prompt_str = ANALYST_PROMPT_TEMPLATE;
    size_t pos = 0;
    while ((pos = prompt_str.find("%SIDE%", pos)) != std::string::npos) {
        prompt_str.replace(pos, 6, side);
        pos += side.length();
    }

    json req_body = {
        {"contents", {{{"parts", {{{"text", prompt_str + "\n\nBRIEFING PACK:\n" + pack.to_briefing_text()}}}}}}},
        {"generationConfig", {
            {"response_mime_type", "application/json"},
            {"temperature", 0.2}
        }}
    };

    auto resp = http::post_json(url, req_body.dump(), 20);
    if (resp.status_code == 200) {
        try {
            auto j = json::parse(resp.body);
            std::string text_output = j["candidates"][0]["content"]["parts"][0]["text"].get<std::string>();
            auto case_json = json::parse(text_output);
            return case_json.get<CaseOutput>();
        } catch (...) {
            // Fallback to mock on parse error
        }
    }

    return generate_mock_case(side, pack);
}

inline std::pair<CaseOutput, CaseOutput> run_dual_analysts(const BriefingPack& pack) {
    // Launch Bull and Bear concurrently using modern C++ std::async threads!
    auto future_bull = std::async(std::launch::async, generate_case, "BULL", pack);
    auto future_bear = std::async(std::launch::async, generate_case, "BEAR", pack);

    return {future_bull.get(), future_bear.get()};
}

} // namespace analysts
