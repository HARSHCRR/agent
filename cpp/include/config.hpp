#pragma once

#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>

namespace config {

inline std::unordered_map<std::string, std::string> load_env_file(const std::string& path = ".env") {
    std::unordered_map<std::string, std::string> env;
    std::ifstream file(path);
    if (!file.is_open()) {
        // Try parent directory
        file.open("../" + path);
    }
    if (!file.is_open()) return env;

    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;
        auto pos = line.find('=');
        if (pos != std::string::npos) {
            std::string key = line.substr(0, pos);
            std::string val = line.substr(pos + 1);
            // Trim whitespace
            key.erase(0, key.find_first_not_of(" \t\r\n"));
            key.erase(key.find_last_not_of(" \t\r\n") + 1);
            val.erase(0, val.find_first_not_of(" \t\r\n"));
            val.erase(val.find_last_not_of(" \t\r\n") + 1);
            env[key] = val;
        }
    }
    return env;
}

inline std::string get_env(const std::string& key, const std::string& default_val = "") {
    static auto file_env = load_env_file();
    const char* sys_val = std::getenv(key.c_str());
    if (sys_val && std::string(sys_val).size() > 0) {
        return std::string(sys_val);
    }
    auto it = file_env.find(key);
    if (it != file_env.end() && !it->second.empty()) {
        return it->second;
    }
    return default_val;
}

inline const std::string GEMINI_MODEL = get_env("GEMINI_MODEL", "gemini-3.8-flash");
inline const std::string GEMINI_API_KEY = get_env("GEMINI_API_KEY", "");
inline const std::string TELEGRAM_BOT_TOKEN = get_env("TELEGRAM_BOT_TOKEN", "8544489986:AAF3WO1sSjj06pKu3M_wqJc0gVIHOs94B50");
inline const std::string TELEGRAM_CHAT_ID = get_env("TELEGRAM_CHAT_ID", "8624502991");
inline const std::string DB_PATH = "data/verdicts_cpp.db";
inline const std::string MARKET_TIMEZONE = "America/New_York";
inline const std::string PACK_CUTOFF_TIME = "09:15";
inline const std::string SESSION_OPEN_TIME = "09:30";

} // namespace config
