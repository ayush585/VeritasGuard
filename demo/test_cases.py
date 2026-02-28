"""
VeritasGuard Demo Test Cases
Run: python -m demo.test_cases
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

TEST_CASES = [
    {
        "name": "Hindi — Communal hoax (water poisoning)",
        "text": "मुस्लिम लोग पानी में जहर मिला रहे हैं",
        "expected_verdict": "FALSE",
        "language": "hi",
    },
    {
        "name": "Hindi — 5G conspiracy",
        "text": "5G टावर से कोरोना फैल रहा है, सरकार छुपा रही है",
        "expected_verdict": "FALSE",
        "language": "hi",
    },
    {
        "name": "Tamil — Garlic COVID cure",
        "text": "பூண்டு சாப்பிட்டால் கொரோனா வராது என்று மருத்துவர்கள் கூறுகிறார்கள்",
        "expected_verdict": "FALSE",
        "language": "ta",
    },
    {
        "name": "English — Vaccine microchip",
        "text": "The Indian government is secretly implanting microchips through COVID vaccines to track citizens",
        "expected_verdict": "FALSE",
        "language": "en",
    },
    {
        "name": "English — Verifiable true claim",
        "text": "India is the most populous country in the world as of 2023",
        "expected_verdict": "TRUE",
        "language": "en",
    },
    {
        "name": "Bengali — WhatsApp hack",
        "text": "WhatsApp মেসেজ খুললেই ফোন হ্যাক হয়ে যাবে",
        "expected_verdict": "MOSTLY_FALSE",
        "language": "bn",
    },
]


async def run_test(client: httpx.AsyncClient, case: dict):
    print(f"\n{'='*60}")
    print(f"TEST: {case['name']}")
    print(f"INPUT: {case['text'][:80]}...")
    print(f"EXPECTED: {case['expected_verdict']}")

    # Submit
    resp = await client.post(f"{BASE_URL}/verify/text", data={"text": case["text"]})
    if resp.status_code != 200:
        print(f"  SUBMIT FAILED: {resp.status_code} {resp.text}")
        return

    vid = resp.json()["verification_id"]
    print(f"  VID: {vid}")

    # Poll for result
    for _ in range(60):  # up to 60 seconds
        await asyncio.sleep(1)
        result = await client.get(f"{BASE_URL}/result/{vid}")
        data = result.json()
        status = data.get("status")
        stage = data.get("stage", "")
        print(f"  ... {status} ({stage})")

        if status == "completed":
            verdict = data.get("verdict", "???")
            confidence = data.get("confidence", 0)
            lang = data.get("detected_language", "?")
            match = "PASS" if verdict == case["expected_verdict"] else "MISMATCH"
            print(f"  RESULT: {verdict} (confidence: {confidence:.0%})")
            print(f"  DETECTED LANG: {lang}")
            print(f"  SUMMARY: {data.get('summary', 'N/A')[:200]}")
            if data.get("native_summary"):
                print(f"  NATIVE: {data['native_summary'][:200]}")
            print(f"  >> {match}")
            return

        if status == "error":
            print(f"  ERROR: {data.get('error')}")
            return

    print("  TIMEOUT after 60s")


async def main():
    print("VeritasGuard Demo Test Suite")
    print(f"Target: {BASE_URL}")

    async with httpx.AsyncClient(timeout=10) as client:
        # Health check
        try:
            resp = await client.get(BASE_URL)
            print(f"Server status: {resp.json()}")
        except Exception as e:
            print(f"Server not reachable: {e}")
            print("Start the server with: python server/main.py")
            return

        for case in TEST_CASES:
            await run_test(client, case)

    print(f"\n{'='*60}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
