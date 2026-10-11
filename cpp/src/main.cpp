#include <iostream>
#include <string>

#include "analysts.hpp"
#include "collector.hpp"
#include "config.hpp"
#include "judge.hpp"
#include "models.hpp"
#include "notifier.hpp"
#include "storage.hpp"

int main(int argc, char* argv[]) {
    bool no_telegram = false;
    bool show_stats = false;
    std::string date_arg = "";
    std::string eod_date = "";
    double eod_ret = 0.0;
    std::string eod_dir = "";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--no-telegram") no_telegram = true;
        else if (arg == "--stats") show_stats = true;
        else if (arg == "--date" && i + 1 < argc) date_arg = argv[++i];
        else if (arg == "--eod" && i + 3 < argc) {
            eod_date = argv[++i];
            eod_ret = std::stod(argv[++i]);
            eod_dir = argv[++i];
        }
    }

    if (show_stats) {
        storage::print_performance_stats();
        return 0;
    }

    if (!eod_date.empty()) {
        storage::record_eod_outcome(eod_date, eod_ret, eod_dir);
        std::cout << "[C++] EOD outcome recorded for " << eod_date << ": " << eod_ret << "% (" << eod_dir << ")\n";
        return 0;
    }

    std::cout << "=== [C++20] Starting Autonomous Pre-Market AI Workflow ===\n";

    // STAGE 1: Briefing Pack Collector
    std::cout << "[Stage 1/6] Ingesting market metrics, economic calendar, and news...\n";
    BriefingPack pack = collector::build_pack(date_arg);
    std::cout << "Briefing Pack compiled for " << pack.date_et << " (" 
              << pack.get_valid_evidence_ids().size() << " valid evidence tokens).\n";

    // STAGE 2: Concurrent Dual Analysts
    std::cout << "[Stage 2/6] Launching concurrent Bull & Bear analyst agents (std::async)...\n";
    auto [bull_case, bear_case] = analysts::run_dual_analysts(pack);

    // STAGE 3: Citation Verification Firewall
    std::cout << "[Stage 3/6] Verifying evidence citations against Briefing Pack...\n";
    bool verified = judge::verify_cases_with_retry(pack, bull_case, bear_case);
    if (!verified) {
        std::cerr << "CRITICAL: Citation firewall rejected cases after retry.\n";
        return 1;
    }
    std::cout << "Citation Firewall passed! All evidence IDs verified.\n";

    // STAGE 4: Blind Anonymization & Order Randomization
    std::cout << "[Stage 4/6] Anonymizing analyst cases and randomizing presentation order...\n";
    auto [case_x, case_y, mapping] = judge::anonymize_and_randomize(bull_case, bear_case);
    std::cout << "Blind mapping established: Case X=" << mapping["X"] << ", Case Y=" << mapping["Y"] << "\n";

    // STAGE 5: Neutral Blind Judge Arbitration
    std::cout << "[Stage 5/6] Submitting cases to Neutral Blind Judge (Gemini)...\n";
    JudgeOutput judge_res = judge::evaluate_cases_blind(pack, case_x, case_y);

    // STAGE 6: Unblind, Persist & Notify
    std::cout << "[Stage 6/6] Unblinding verdict, persisting to SQLite, and dispatching notification...\n";
    json final_record = judge::unblind_verdict(judge_res, mapping);

    long long row_id = storage::save_run(
        pack.date_et,
        pack.to_briefing_text(),
        bull_case,
        bear_case,
        final_record
    );
    std::cout << "Execution record saved to SQLite (ID: " << row_id << ")\n";

    if (!no_telegram) {
        std::string alert_msg = notifier::format_telegram_message(pack.date_et, final_record);
        bool sent = notifier::send_telegram_alert(alert_msg);
        std::cout << "Telegram Alert Dispatched: " << (sent ? "SUCCESS" : "SKIPPED/FAILED") << "\n";
    }

    std::cout << "\n===================================================\n";
    std::cout << "FINAL VERDICT: " << final_record["verdict"].get<std::string>() << "\n";
    std::cout << "CONFIDENCE:    " << final_record["confidence"].get<std::string>() << "\n";
    std::cout << "WINNING BIAS:  " << final_record["unblinded_winner"].get<std::string>() << "\n";
    std::cout << "REASONING:     " << final_record["reasoning"].get<std::string>() << "\n";
    std::cout << "===================================================\n";

    return 0;
}
