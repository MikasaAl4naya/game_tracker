import requests
import os
import sys

BASE_URL = "http://127.0.0.1:8080"
ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "lootozavr_admin_secret_2026")

session = requests.Session()
session.trust_env = False  # Bypass local system proxies for 127.0.0.1

def run_security_tests():
    print("=" * 60)
    print("🔒 RUNNING LOOTOZAVR SECURITY & DEPLOYMENT AUDIT TESTS")
    print("=" * 60)

    # 1. Test Swagger / OpenAPI endpoints are disabled (404)
    print("\n[TEST 1] Verifying Swagger & OpenAPI endpoints return 404...")
    for path in ["/docs", "/redoc", "/openapi.json"]:
        res = session.get(f"{BASE_URL}{path}")
        assert res.status_code == 404, f"Expected 404 for {path}, got {res.status_code}"
        print(f"  PASS: {path} -> 404 Not Found (Disabled)")

    # 2. Test Security Headers
    print("\n[TEST 2] Verifying Security Headers on response...")
    res = session.get(f"{BASE_URL}/")
    assert res.status_code == 200, f"Expected 200 for /, got {res.status_code}"
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff", "Missing X-Content-Type-Options: nosniff"
    assert headers.get("X-Frame-Options") == "SAMEORIGIN", "Missing X-Frame-Options: SAMEORIGIN"
    assert "strict-origin-when-cross-origin" in headers.get("Referrer-Policy", ""), "Missing Referrer-Policy"
    print("  PASS: X-Content-Type-Options: nosniff")
    print("  PASS: X-Frame-Options: SAMEORIGIN")
    print("  PASS: Referrer-Policy: strict-origin-when-cross-origin")

    # 3. Test Admin Protected Task Endpoints (Must be 403 without valid key)
    print("\n[TEST 3] Testing Admin Task endpoints security (403 without key)...")
    protected_paths = [
        "/api/tasks/reparse_all",
        "/api/tasks/force_check",
        "/api/tasks/fill_missing",
        "/api/catalog/sync",
        "/api/catalog/sync_funpay",
        "/api/catalog/backfill_appids",
        "/api/catalog/backfill_stats",
    ]

    for p in protected_paths:
        # Without key
        res = session.post(f"{BASE_URL}{p}")
        assert res.status_code == 403, f"Expected 403 for {p} without auth, got {res.status_code}"
        
        # With fake key
        res_fake = session.post(f"{BASE_URL}{p}", headers={"X-Admin-Key": "fake_hacker_token"})
        assert res_fake.status_code == 403, f"Expected 403 for {p} with invalid auth, got {res_fake.status_code}"
        print(f"  PASS: {p} rejected unauthorized access (403 Forbidden)")

    # 4. Test Admin Endpoint with Valid Key (Must succeed 200)
    print("\n[TEST 4] Testing Admin Task endpoint with valid key...")
    valid_res = session.post(
        f"{BASE_URL}/api/tasks/force_check",
        headers={"X-Admin-Key": ADMIN_KEY}
    )
    assert valid_res.status_code == 200, f"Expected 200 with valid key, got {valid_res.status_code}"
    print(f"  PASS: /api/tasks/force_check succeeded with valid X-Admin-Key (200 OK)")

    # 5. Test Input Validation on /api/track
    print("\n[TEST 5] Testing Input Validation on /api/track...")
    # Negative price
    bad_price_res = session.post(
        f"{BASE_URL}/api/track",
        json={"game_name": "Palworld", "target_price": -100, "chat_id": 123456}
    )
    assert bad_price_res.status_code == 400, f"Expected 400 for negative price, got {bad_price_res.status_code}"
    print("  PASS: Negative target_price rejected (400 Bad Request)")

    # Negative chat_id
    bad_chat_res = session.post(
        f"{BASE_URL}/api/track",
        json={"game_name": "Palworld", "target_price": 500, "chat_id": -99}
    )
    assert bad_chat_res.status_code == 400, f"Expected 400 for negative chat_id, got {bad_chat_res.status_code}"
    print("  PASS: Invalid chat_id rejected (400 Bad Request)")

    # 6. Test Core Public Endpoints Still Function Normally
    print("\n[TEST 6] Testing Core Public Services...")
    pop_res = session.get(f"{BASE_URL}/api/catalog/popular?mode=new")
    assert pop_res.status_code == 200, f"Expected 200 for popular games, got {pop_res.status_code}"
    assert len(pop_res.json().get("games", [])) > 0, "Expected popular games list"
    print("  PASS: /api/catalog/popular returned active catalog")

    manifest_res = session.get(f"{BASE_URL}/manifest.json")
    assert manifest_res.status_code == 200, f"Expected 200 for manifest.json, got {manifest_res.status_code}"
    print("  PASS: /manifest.json accessible")

    sw_res = session.get(f"{BASE_URL}/sw.js")
    assert sw_res.status_code == 200, f"Expected 200 for sw.js, got {sw_res.status_code}"
    print("  PASS: /sw.js accessible")

    print("\n" + "=" * 60)
    print("🛡️  ALL 6 SECURITY & DEPLOYMENT AUDIT CHECKS PASSED 100%!")
    print("=" * 60)

if __name__ == "__main__":
    run_security_tests()
