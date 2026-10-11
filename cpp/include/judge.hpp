#pragma once

#include <algorithm>
#include <iostream>
#include <random>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "analysts.hpp"
#include "config.hpp"
#include "http_client.hpp"
#include "models.hpp"

namespace judge {

inline std::pair<bool, std::vector<std::string>> validate_citations(
    const CaseOutput& case_out,
    const std::unordered_set<std::string>& valid_ids
) {
    std::vector<std::string> invalid_ids;
    for (const auto& driver : case_out.key_drivers) {
        for (const auto& eid : driver.evidence_ids) {
            std::string clean = eid;
            std::transform(clean.begin(), clean.end(), clean.begin(), ::toupper);
            if (valid_ids.find(clean) == valid_ids.end()) {
                invalid_ids.push_back(eid);
            }
        }
    }
    return {invalid_ids.empty(), invalid_ids};
}

inline bool verify_cases_with_retry(
    const BriefingPack& pack,
    CaseOutput& bull_case,
    CaseOutput& bear_case
) {
    auto valid_ids = pack.get_valid_evidence_ids();

    auto [bull_ok, bull_bad] = validate_citations(bull_case, valid_ids);
    if (!bull_ok) {
        // 1-retry loop
        bull_case = analysts::generate_case("BULL", pack);
        auto [retry_ok, _] = validate_citations(bull_case, valid_ids);
        if (!retry_ok) return false;
    }

    auto [bear_ok, bear_bad] = validate_citations(bear_case, valid_ids);
    if (!bear_ok) {
        // 1-retry loop
        bear_case = analysts::generate_case("BEAR", pack);
        auto [retry_ok, _] = validate_citations(bear_case, valid_ids);
        if (!retry_ok) return false;
    }

    return true;
}

inline std::tuple<json, json, std::unordered_map<std::string, std::string>> anonymize_and_randomize(
    const CaseOutput& bull_case,
    const CaseOutput& bear_case
) {
    json j_bull = bull_case;
    json j_bear = bear_case;
    j_bull.erase("side");
    j_bear.erase("side");

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> coin(0, 1);

    std::unordered_map<std::string, std::string> mapping;
    if (coin(gen) == 0) {
        mapping["X"] = "BULL";
        mapping["Y"] = "BEAR";
        return {j_bull, j_bear, mapping};
    } else {
        mapping["X"] = "BEAR";
        mapping["Y"] = "BULL";
        return {j_bear, j_bull, mapping};
    }
}

inline JudgeOutput generate_mock_judge(const BriefingPack& pack) {
    JudgeOutput out;
    bool has_morning_print = false;
    for (const auto& e : pack.events_today) {
        if (e.time_et <= "10:00") { has_morning_print = true; break; }
    }

    if (has_morning_print) {
        out.verdict = "sideways";
        out.confidence = "low";
        out.winning_case = "neither";
        out.deciding_factors = {
            "Morning economic release catalyst uncertainty",
            "Compression in VIX vs yield drag tension"
        };
        out.reasoning = "Evidence is balanced ahead of critical early macro releases. Catalyst uncertainty limits directional conviction.";
        out.events_to_watch = {"Average Hourly Earnings", "Non-Farm Payrolls"};
        out.caveats = "Pending prints carry immediate invalidation risk across key drivers.";
    } else {
        out.verdict = "bullish";
        out.confidence = "medium";
        out.winning_case = "X";
        out.deciding_factors = {
            "Technical consolidation above key moving averages",
            "Low volatility index compression"
        };
        out.reasoning = "Technical stability and calm options pricing provide slightly superior evidence over macro yield concerns.";
        out.events_to_watch = {"Cash open volume expansion"};
        out.caveats = "Elevated 10Y yield remains a persistent valuation cap.";
    }
    return out;
}

inline JudgeOutput evaluate_cases_blind(
    const BriefingPack& pack,
    const json& case_x,
    const json& case_y
) {
    if (config::GEMINI_API_KEY.empty() || config::GEMINI_API_KEY == "your_gemini_api_key_here") {
        return generate_mock_judge(pack);
    }

    std::string url = "https://generativelanguage.googleapis.com/v1beta/models/" + 
                      config::GEMINI_MODEL + ":generateContent?key=" + config::GEMINI_API_KEY;

    std::string prompt = 
        "You are a neutral institutional risk reviewer. Two analysts wrote opposing cases about NAS100. "
        "Decide whether evidence points to bullish, bearish, or sideways for today.\n\n"
        "BRIEFING PACK:\n" + pack.to_briefing_text() + "\n\n"
        "CASE X:\n" + case_x.dump(2) + "\n\n"
        "CASE Y:\n" + case_y.dump(2) + "\n\n"
        "Output JSON only matching: {verdict, confidence, winning_case, deciding_factors, reasoning, events_to_watch, caveats}";

    json req_body = {
        {"contents", {{{"parts", {{{"text", prompt}}}}}}},
        {"generationConfig", {
            {"response_mime_type", "application/json"},
            {"temperature", 0.1}
        }}
    };

    auto resp = http::post_json(url, req_body.dump(), 20);
    if (resp.status_code == 200) {
        try {
            auto j = json::parse(resp.body);
            std::string text_output = j["candidates"][0]["content"]["parts"][0]["text"].get<std::string>();
            return json::parse(text_output).get<JudgeOutput>();
        } catch (...) {}
    }

    return generate_mock_judge(pack);
}

inline json unblind_verdict(
    const JudgeOutput& judge_res,
    const std::unordered_map<std::string, std::string>& mapping
) {
    std::string actual_winner = "NEITHER";
    if (judge_res.winning_case == "X" || judge_res.winning_case == "Y") {
        auto it = mapping.find(judge_res.winning_case);
        if (it != mapping.end()) actual_winner = it->second;
    }

    json out = {
        {"verdict", judge_res.verdict},
        {"confidence", judge_res.confidence},
        {"blind_winner", judge_res.winning_case},
        {"unblinded_winner", actual_winner},
        {"mapping", mapping},
        {"deciding_factors", judge_res.deciding_factors},
        {"reasoning", judge_res.reasoning},
        {"events_to_watch", judge_res.events_to_watch},
        {"caveats", judge_res.caveats}
    };
    return out;
}

} // namespace judge
