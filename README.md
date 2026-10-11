# ai-lab
---

## ⚡ High-Performance C++20 Implementation (`cpp/`)

A production-grade **C++20** implementation is included for high-performance quantitative setups:

* **Modern C++20 Architecture**: Zero-overhead memory footprint, structured JSON contracts via `nlohmann/json`.
* **Asynchronous Concurrency**: Parallel Bull/Bear agent calls via `std::async(std::launch::async, ...)`.
* **Native Storage**: Embedded SQLite3 C-API audit trail (`verdicts_cpp.db`).
* **Networking**: Direct HTTP GET/POST via native `libcurl`.

### Build & Run the C++ Engine:
```bash
cd cpp
mkdir -p build && cd build
cmake ..
make -j4

# Execute Pre-Market AI Workflow
./quant_agent

# View Performance Analytics
./quant_agent --stats
```
