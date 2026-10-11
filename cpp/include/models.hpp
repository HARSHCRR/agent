#pragma once

#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

#include "json.hpp"

using json = nlohmann::json;

// =====================================================================
// 1. BRIEFING PACK STRUCTS
// =====================================================================

struct PriceMetrics {
    double prev_open = 0.0;
    double prev_high = 0.0;
    double prev_low = 0.0;
    double prev_close = 0.0;
    double volume_vs_20d_avg_pct = 0.0;
    double overnight_futures_change_pct = 0.0;
    double gap_vs_prev_close_pct = 0.0;
    double vix = 0.0;
    double vix_change = 0.0;
    double us10y = 0.0;
    double us10y_change = 0.0;
    double dxy = 0.0;
    double dxy_change = 0.0;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(
    PriceMetrics,
    prev_open, prev_high, prev_low, prev_close,
    volume_vs_20d_avg_pct, overnight_futures_change_pct, gap_vs_prev_close_pct,
    vix, vix_change, us10y, us10y_change, dxy, dxy_change
)

struct CalendarEvent {
    std::string id;       // e.g. "E1"
    std::string time_et;  // e.g. "08:30"
    std::string event;    // e.g. "CPI m/m"
    std::string forecast = "N/A";
    std::string previous = "N/A";
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(CalendarEvent, id, time_et, event, forecast, previous)

struct PastCalendarEvent {
    std::string id;       // e.g. "Y1"
    std::string event;
    std::string actual;
    std::string expected = "N/A";
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(PastCalendarEvent, id, event, actual, expected)

struct HeadlineItem {
    std::string id;       // e.g. "H1"
    std::string time_et;  // e.g. "07:42"
    std::string source;
    std::string headline;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(HeadlineItem, id, time_et, source, headline)

struct BriefingPack {
    std::string date_et;
    std::string open_et = "09:30";
    std::string pack_built_et = "09:15";
    PriceMetrics price;
    std::vector<CalendarEvent> events_today;
    std::vector<PastCalendarEvent> events_yesterday;
    std::vector<HeadlineItem> headlines;
    std::vector<std::string> failed_sources;

    std::unordered_set<std::string> get_valid_evidence_ids() const {
        std::unordered_set<std::string> valid_ids = {"PRICE"};
        for (const auto& e : events_today) valid_ids.insert(e.id);
        for (const auto& y : events_yesterday) valid_ids.insert(y.id);
        for (const auto& h : headlines) valid_ids.insert(h.id);
        return valid_ids;
    }

    std::string to_briefing_text() const {
        std::ostringstream oss;
        oss << "DATE_ET: " << date_et << " | OPEN_ET: " << open_et
            << " | PACK_BUILT_ET: " << pack_built_et << "\n\n";

        oss << "[PRICE]\n"
            << "prev_day: O=" << price.prev_open << " H=" << price.prev_high
            << " L=" << price.prev_low << " C=" << price.prev_close
            << " | volume_vs_20d_avg=" << price.volume_vs_20d_avg_pct
            << "% overnight_futures_change=" << price.overnight_futures_change_pct
            << "% | gap_vs_prev_close=" << price.gap_vs_prev_close_pct
            << "% VIX=" << price.vix << " (chg " << price.vix_change
            << ") | US10Y=" << price.us10y << " (chg " << price.us10y_change
            << ") | DXY=" << price.dxy << " (chg " << price.dxy_change << ")\n\n";

        oss << "[EVENTS_TODAY] (time ET | event | forecast | previous)\n";
        if (events_today.empty()) {
            oss << "none\n";
        } else {
            for (const auto& e : events_today) {
                oss << e.id << " | " << e.time_et << " | " << e.event << " | "
                    << e.forecast << " | " << e.previous << "\n";
            }
        }
        oss << "\n";

        oss << "[EVENTS_YESTERDAY] (event | actual | expected)\n";
        if (events_yesterday.empty()) {
            oss << "none\n";
        } else {
            for (const auto& y : events_yesterday) {
                oss << y.id << " | " << y.event << " | " << y.actual << " | "
                    << y.expected << "\n";
            }
        }
        oss << "\n";

        oss << "[HEADLINES] (published before " << pack_built_et << " ET only)\n";
        if (headlines.empty()) {
            oss << "none\n";
        } else {
            for (const auto& h : headlines) {
                oss << h.id << " | " << h.time_et << " | " << h.source << " | "
                    << h.headline << "\n";
            }
        }
        oss << "\n";

        oss << "[DATA_STATUS] failed_sources: [";
        if (failed_sources.empty()) {
            oss << "none";
        } else {
            for (size_t i = 0; i < failed_sources.size(); ++i) {
                oss << failed_sources[i] << (i + 1 < failed_sources.size() ? ", " : "");
            }
        }
        oss << "]";

        return oss.str();
    }
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(
    BriefingPack,
    date_et, open_et, pack_built_et, price,
    events_today, events_yesterday, headlines, failed_sources
)

// =====================================================================
// 2. ANALYST CASE STRUCTS
// =====================================================================

struct CaseDriver {
    std::string point;
    std::vector<std::string> evidence_ids;
    std::string horizon; // "premarket" | "us_session" | "multi_day"
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(CaseDriver, point, evidence_ids, horizon)

struct CaseOutput {
    std::string side; // "BULL" | "BEAR"
    std::string headline;
    std::vector<CaseDriver> key_drivers;
    std::string strongest_counterpoint;
    std::string invalidation;
    std::vector<std::string> data_gaps;

    void validate() const {
        if (key_drivers.size() != 3) {
            throw std::runtime_error("Validation error: key_drivers must contain exactly 3 items.");
        }
    }
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(
    CaseOutput,
    side, headline, key_drivers, strongest_counterpoint, invalidation, data_gaps
)

// =====================================================================
// 3. BLIND JUDGE STRUCTS
// =====================================================================

struct JudgeOutput {
    std::string verdict;         // "bullish" | "bearish" | "sideways"
    std::string confidence;      // "low" | "medium" | "high"
    std::string winning_case;    // "X" | "Y" | "neither"
    std::vector<std::string> deciding_factors;
    std::string reasoning;
    std::vector<std::string> events_to_watch;
    std::string caveats;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE(
    JudgeOutput,
    verdict, confidence, winning_case, deciding_factors,
    reasoning, events_to_watch, caveats
)
