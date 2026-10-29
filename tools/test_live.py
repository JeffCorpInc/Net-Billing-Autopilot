import urllib.request, ssl, json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://net-billing-autopilot.vercel.app"
endpoints = [
    ("/", "text/html"),
    ("/apply", "text/html"),
    ("/case/C01", "text/html"),
    ("/evaluate", "text/html"),
    ("/about", "text/html"),
    ("/api/health", "application/json"),
    ("/api/cases", "application/json"),
    ("/api/ocr/status", "application/json"),
    ("/static/styles.css", "text/css"),
    ("/static/new_case.js", "text/javascript"),
    ("/static/dashboard.js", "text/javascript"),
]

print("=== VERCEL PRODUCTION VERIFICATION ===")
for path, expected_ct in endpoints:
    url = base + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            content = resp.read()
            ct = resp.headers.get("Content-Type", "")
            short_ct = ct.split(";")[0]
            print(f"{path:22} -> 200 OK | Type: {short_ct:20} | Size: {len(content):,} bytes")
    except Exception as e:
        print(f"{path:22} -> FAILED: {e}")

# Verify case count
try:
    req = urllib.request.Request(base + "/api/cases", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"\nAPI Cases Count: {len(data)} (Expected: 21)")
        ready = [c["case_id"] for c in data if c.get("overall") == "READY"]
        not_ready = [c["case_id"] for c in data if c.get("overall") == "NOT_READY"]
        print(f"READY cases: {len(ready)}, NOT_READY cases: {len(not_ready)}")
except Exception as e:
    print(f"Cases parse error: {e}")

# Verify live LLM copilot
try:
    req = urllib.request.Request(
        base + "/api/assistant/chat",
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"},
        data=json.dumps({"messages": [{"role": "user", "content": "What is the maximum solar capacity allowed for net billing in Karachi?"}]}).encode("utf-8"),
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
        ans = json.loads(resp.read().decode("utf-8"))
        print("\nAI Copilot Test:")
        print(f"Status: {resp.status}")
        print(f"Provider: {ans.get('provider')}, Model: {ans.get('model')}")
        reply = ans.get("reply", "")
        print(f"Reply snippet: {reply[:150]}...")
except Exception as e:
    print(f"AI Copilot test error: {e}")
