#pragma once

#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <sqlite3.h>
#include <string>

#include "config.hpp"
#include "json.hpp"

namespace storage {

inline void init_db(const std::string& db_path = config::DB_PATH) {
    sqlite3* db = nullptr;
    if (sqlite3_open(db_path.c_str(), &db) != SQLITE_OK) {
        std::cerr << "Failed to open SQLite DB: " << sqlite3_errmsg(db) << "\n";
        return;
    }

    const char* sql = 
        "CREATE TABLE IF NOT EXISTS verdicts ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  run_date TEXT NOT NULL,"
        "  created_at TEXT NOT NULL,"
        "  pack_text TEXT NOT NULL,"
        "  bull_case TEXT NOT NULL,"
        "  bear_case TEXT NOT NULL,"
        "  blind_mapping TEXT NOT NULL,"
        "  blind_winner TEXT NOT NULL,"
        "  unblinded_winner TEXT NOT NULL,"
        "  verdict TEXT NOT NULL,"
        "  confidence TEXT NOT NULL,"
        "  deciding_factors TEXT NOT NULL,"
        "  reasoning TEXT NOT NULL,"
        "  events_to_watch TEXT NOT NULL,"
        "  caveats TEXT NOT NULL,"
        "  actual_return_pct REAL DEFAULT NULL,"
        "  actual_direction TEXT DEFAULT NULL,"
        "  is_correct INTEGER DEFAULT NULL"
        ");";

    char* err_msg = nullptr;
    sqlite3_exec(db, sql, nullptr, nullptr, &err_msg);
    if (err_msg) {
        sqlite3_free(err_msg);
    }
    sqlite3_close(db);
}

inline long long save_run(
    const std::string& run_date,
    const std::string& pack_text,
    const nlohmann::json& bull_case,
    const nlohmann::json& bear_case,
    const nlohmann::json& unblinded_result,
    const std::string& db_path = config::DB_PATH
) {
    init_db(db_path);
    sqlite3* db = nullptr;
    if (sqlite3_open(db_path.c_str(), &db) != SQLITE_OK) return -1;

    auto now = std::chrono::system_clock::now();
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm_buf;
    gmtime_r(&t, &tm_buf);
    char time_str[64];
    std::strftime(time_str, sizeof(time_str), "%Y-%m-%dT%H:%M:%SZ", &tm_buf);

    const char* sql = 
        "INSERT INTO verdicts ("
        "  run_date, created_at, pack_text, bull_case, bear_case,"
        "  blind_mapping, blind_winner, unblinded_winner,"
        "  verdict, confidence, deciding_factors, reasoning,"
        "  events_to_watch, caveats"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);";

    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, nullptr) != SQLITE_OK) {
        sqlite3_close(db);
        return -1;
    }

    std::string b_str = bull_case.dump();
    std::string r_str = bear_case.dump();
    std::string map_str = unblinded_result.value("mapping", nlohmann::json::object()).dump();
    std::string b_win = unblinded_result.value("blind_winner", "");
    std::string u_win = unblinded_result.value("unblinded_winner", "");
    std::string verd = unblinded_result.value("verdict", "");
    std::string conf = unblinded_result.value("confidence", "");
    std::string factors_str = unblinded_result.value("deciding_factors", nlohmann::json::array()).dump();
    std::string reason = unblinded_result.value("reasoning", "");
    std::string watch_str = unblinded_result.value("events_to_watch", nlohmann::json::array()).dump();
    std::string caveats = unblinded_result.value("caveats", "");

    sqlite3_bind_text(stmt, 1, run_date.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, time_str, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, pack_text.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 4, b_str.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 5, r_str.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 6, map_str.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 7, b_win.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 8, u_win.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 9, verd.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 10, conf.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 11, factors_str.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 12, reason.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 13, watch_str.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 14, caveats.c_str(), -1, SQLITE_TRANSIENT);

    sqlite3_step(stmt);
    long long row_id = sqlite3_last_insert_rowid(db);
    sqlite3_finalize(stmt);
    sqlite3_close(db);

    return row_id;
}

inline void record_eod_outcome(
    const std::string& run_date,
    double actual_return_pct,
    const std::string& actual_direction,
    const std::string& db_path = config::DB_PATH
) {
    init_db(db_path);
    sqlite3* db = nullptr;
    if (sqlite3_open(db_path.c_str(), &db) != SQLITE_OK) return;

    std::string sql = "SELECT id, verdict FROM verdicts WHERE run_date = '" + run_date + "';";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db, sql.c_str(), -1, &stmt, nullptr) == SQLITE_OK) {
        while (sqlite3_step(stmt) == SQLITE_ROW) {
            int id = sqlite3_column_int(stmt, 0);
            std::string verdict = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
            
            int is_correct = 0;
            if (verdict == "bullish" && actual_direction == "up") is_correct = 1;
            else if (verdict == "bearish" && actual_direction == "down") is_correct = 1;
            else if (verdict == "sideways" && actual_direction == "flat") is_correct = 1;

            std::string update_sql = "UPDATE verdicts SET actual_return_pct = " + std::to_string(actual_return_pct) +
                                     ", actual_direction = '" + actual_direction + "', is_correct = " + std::to_string(is_correct) +
                                     " WHERE id = " + std::to_string(id) + ";";
            sqlite3_exec(db, update_sql.c_str(), nullptr, nullptr, nullptr);
        }
        sqlite3_finalize(stmt);
    }
    sqlite3_close(db);
}

inline void print_performance_stats(const std::string& db_path = config::DB_PATH) {
    init_db(db_path);
    sqlite3* db = nullptr;
    if (sqlite3_open(db_path.c_str(), &db) != SQLITE_OK) return;

    std::cout << "\n=== [C++] FORWARD-TEST PERFORMANCE DASHBOARD ===\n";
    const char* count_sql = "SELECT COUNT(*) FROM verdicts;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db, count_sql, -1, &stmt, nullptr) == SQLITE_OK) {
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            std::cout << "Total Pre-Market Runs: " << sqlite3_column_int(stmt, 0) << "\n";
        }
        sqlite3_finalize(stmt);
    }

    const char* eval_sql = "SELECT COUNT(*), SUM(is_correct), AVG(is_correct) * 100.0 FROM verdicts WHERE is_correct IS NOT NULL;";
    if (sqlite3_prepare_v2(db, eval_sql, -1, &stmt, nullptr) == SQLITE_OK) {
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            int evaluated = sqlite3_column_int(stmt, 0);
            int correct = sqlite3_column_int(stmt, 1);
            double win_rate = sqlite3_column_double(stmt, 2);
            std::cout << "Evaluated Runs: " << evaluated << "\n";
            std::cout << "Correct Predictions: " << correct << "\n";
            std::cout << "Overall Directional Win Rate: " << std::fixed << std::setprecision(1) << win_rate << "%\n";
        }
        sqlite3_finalize(stmt);
    }
    std::cout << "=================================================\n\n";
    sqlite3_close(db);
}

} // namespace storage
