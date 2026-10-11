#pragma once

#include <iostream>
#include <sstream>
#include <string>

#include "config.hpp"
#include "http_client.hpp"
#include "json.hpp"

namespace notifier {

inline std::string format_telegram_message(
    const std::string& run_date,
    const nlohmann::json& res
) {
    std::string verdict = res.value("verdict", "sideways");
    std::string confidence = res.value("confidence", "low");
    std::string unblinded_winner = res.value("unblinded_winner", "NEITHER");
    std::string blind_winner = res.value("blind_winner", "neither");
    std::string reasoning = res.value("reasoning", "");
    std::string caveats = res.value("caveats", "");

    std::string badge = "🟡 SIDEWAYS / NEUTRAL";
    if (verdict == "bullish") badge = "🟢 BULLISH";
    else if (verdict == "bearish") badge = "🔴 BEARISH";

    std::ostringstream oss;
    oss << "📊 *NAS100 PRE-MARKET VERDICT* | `" << run_date << "`\n"
        << "━━━━━━━━━━━━━━━━━━━━━━\n"
        << "*Verdict:* " << badge << "\n"
        << "*Confidence:* `" << confidence << "`\n"
        << "*Winning Case:* `" << unblinded_winner << "` _(Blind Case " << blind_winner << ")_\n\n"
        << "⚖️ *Deciding Factors:*\n";

    if (res.contains("deciding_factors") && res["deciding_factors"].is_array()) {
        for (const auto& item : res["deciding_factors"]) {
            oss << "  • " << item.get<std::string>() << "\n";
        }
    } else {
        oss << "  • Balanced evidence\n";
    }

    oss << "\n🧠 *Rationale:*\n" << reasoning << "\n\n"
        << "⚠️ *Caveats:* " << caveats << "\n"
        << "━━━━━━━━━━━━━━━━━━━━━━\n"
        << "⚡ _High-Performance C++20 Dual-Analyst AI Workflow_";

    return oss.str();
}

inline bool send_telegram_alert(
    const std::string& message,
    const std::string& token = config::TELEGRAM_BOT_TOKEN,
    const std::string& chat_id = config::TELEGRAM_CHAT_ID
) {
    if (token.empty() || chat_id.empty() || token.find("your_") != std::string::npos) {
        return false;
    }

    std::string url = "https://api.telegram.org/bot" + token + "/sendMessage";
    nlohmann::json payload = {
        {"chat_id", chat_id},
        {"text", message},
        {"parse_mode", "Markdown"},
        {"disable_web_page_preview", true}
    };

    auto resp = http::post_json(url, payload.dump(), 10);
    return resp.status_code == 200;
}

} // namespace notifier
