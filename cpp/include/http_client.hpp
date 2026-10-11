#pragma once

#include <curl/curl.h>
#include <iostream>
#include <string>
#include <vector>

namespace http {

struct HttpResponse {
    long status_code = 0;
    std::string body;
    std::string error_message;
};

inline size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    std::string* response_str = static_cast<std::string*>(userp);
    response_str->append(static_cast<char*>(contents), total_size);
    return total_size;
}

inline HttpResponse get(const std::string& url, long timeout_seconds = 10) {
    HttpResponse resp;
    CURL* curl = curl_easy_init();
    if (!curl) {
        resp.error_message = "Failed to initialize CURL";
        return resp;
    }

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &resp.body);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_seconds);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)");

    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        resp.error_message = curl_easy_strerror(res);
    } else {
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &resp.status_code);
    }

    curl_easy_cleanup(curl);
    return resp;
}

inline HttpResponse post_json(
    const std::string& url,
    const std::string& json_payload,
    long timeout_seconds = 15
) {
    HttpResponse resp;
    CURL* curl = curl_easy_init();
    if (!curl) {
        resp.error_message = "Failed to initialize CURL";
        return resp;
    }

    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_payload.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &resp.body);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_seconds);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "QuantAgentCPP/1.0");

    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        resp.error_message = curl_easy_strerror(res);
    } else {
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &resp.status_code);
    }

    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    return resp;
}

} // namespace http
