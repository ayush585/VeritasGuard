"""
VeritasGuard Demo Test Cases
Run:
  python -m demo.test_cases --profile stable
  python -m demo.test_cases --profile extended --timeout 90
"""

import argparse
import asyncio

import httpx

BASE_URL = "http://localhost:8000"

STABLE_TEST_CASES = [
    {
        "name": "Hindi - Communal hoax (water poisoning)",
        "text": "सावधान! मुस्लिम लोग पानी में जहर मिला रहे हैं, तुरंत शेयर करें।",
        "expected_verdict": "FALSE",
        "language": "hi",
    },
    {
        "name": "Tamil - Garlic COVID cure",
        "text": "பூண்டு சாப்பிட்டால் கொரோனா வராது என்று கூறப்படுகிறது.",
        "expected_verdict": "FALSE",
        "language": "ta",
    },
    {
        "name": "English - Vaccine microchip",
        "text": "The Indian government is secretly implanting microchips through COVID vaccines.",
        "expected_verdict": "FALSE",
        "language": "en",
    },
    {
        "name": "Bengali - WhatsApp hack panic",
        "text": "WhatsApp মেসেজ খুললেই ফোন হ্যাক হয়ে যাবে, সবাইকে পাঠাও।",
        "expected_verdict": "MOSTLY_FALSE",
        "language": "bn",
    },
    {
        "name": "Marathi - Hot water cures COVID",
        "text": "दर १५ मिनिटांनी गरम पाणी पिल्याने कोरोना निघून जातो.",
        "expected_verdict": "FALSE",
        "language": "mr",
    },
    {
        "name": "Telugu - 5G conspiracy",
        "text": "5G టవర్ల వల్ల కరోనా వ్యాపిస్తుంది.",
        "expected_verdict": "FALSE",
        "language": "te",
    },
]

EXTENDED_TEST_CASES = STABLE_TEST_CASES + [
    {
        "name": "Kannada - Child lifting panic alert",
        "text": "ಈ ಪ್ರದೇಶದಲ್ಲಿ ಮಕ್ಕಳ ಕಳ್ಳರ ಗುಂಪು ಬಂದಿದೆ, ಈ ಸಂದೇಶವನ್ನು ತಕ್ಷಣ ಹಂಚಿ.",
        "expected_verdict": "MOSTLY_FALSE",
        "language": "kn",
    },
    {
        "name": "Malayalam - Hot water cures COVID",
        "text": "ഓരോ 15 മിനിറ്റിലും ചൂടുവെള്ളം കുടിച്ചാൽ കൊറോണ പോകും.",
        "expected_verdict": "FALSE",
        "language": "ml",
    },
    {
        "name": "Punjabi - 5G conspiracy",
        "text": "5G ਟਾਵਰਾਂ ਕਰਕੇ ਕੋਰੋਨਾ ਫੈਲਦਾ ਹੈ।",
        "expected_verdict": "FALSE",
        "language": "pa",
    },
    {
        "name": "Urdu - Vaccine microchip rumor",
        "text": "حکومت ویکسین کے ذریعے لوگوں میں مائیکروچپ لگا رہی ہے۔",
        "expected_verdict": "FALSE",
        "language": "ur",
    },
]

PROFILES = {
    "stable": STABLE_TEST_CASES,
    "extended": EXTENDED_TEST_CASES,
}


async def run_test(client: httpx.AsyncClient, case: dict, timeout_seconds: int) -> tuple[bool, bool]:
    print(f"\n{'=' * 60}")
    print(f"TEST: {case['name']}")
    print(f"INPUT: {case['text'][:100]}...")
    print(f"EXPECTED: {case['expected_verdict']}")

    resp = await client.post(f"{BASE_URL}/verify/text", data={"text": case["text"]})
    if resp.status_code != 200:
        print(f"  SUBMIT FAILED: {resp.status_code} {resp.text}")
        return False, False

    vid = resp.json()["verification_id"]
    print(f"  VID: {vid}")

    for _ in range(timeout_seconds):
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
            match = verdict == case["expected_verdict"]
            print(f"  RESULT: {verdict} (confidence: {confidence:.0%})")
            print(f"  DETECTED LANG: {lang}")
            print(f"  SEARCH: {data.get('search_provider', 'n/a')} ({data.get('search_results_count', 0)} results)")
            print(f"  AUDIO: {data.get('audio_status', 'n/a')}")
            print(f"  SUMMARY: {data.get('summary', 'N/A')[:220]}")
            if data.get("native_summary"):
                print(f"  NATIVE: {data['native_summary'][:220]}")
            if data.get("warnings"):
                print(f"  WARNINGS: {data['warnings'][:2]}")
            print("  >> PASS" if match else "  >> MISMATCH")
            return True, match

        if status == "error":
            print(f"  ERROR: {data.get('error')}")
            return True, False

    print(f"  TIMEOUT after {timeout_seconds}s")
    return False, False


async def main(profile: str, timeout_seconds: int):
    print("VeritasGuard Demo Test Suite")
    print(f"Target: {BASE_URL}")
    print(f"Profile: {profile}")

    cases = PROFILES[profile]
    completed = 0
    passed = 0
    timeouts = 0

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(BASE_URL)
            print(f"Server status: {resp.json()}")
        except Exception as e:
            print(f"Server not reachable: {e}")
            print("Start the server with: python -m uvicorn server.main:app --reload")
            return

        for case in cases:
            finished, match = await run_test(client, case, timeout_seconds)
            if finished:
                completed += 1
            else:
                timeouts += 1
            if match:
                passed += 1

    pass_rate = (passed / len(cases)) * 100 if cases else 0.0
    print(f"\n{'=' * 60}")
    print(f"Completed: {completed}/{len(cases)}")
    print(f"Timeouts: {timeouts}")
    print(f"Pass rate: {pass_rate:.1f}%")
    if profile == "stable":
        print("Stable profile target: >=90% pass rate and zero timeout.")
    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VeritasGuard demo test suite")
    parser.add_argument("--profile", choices=["stable", "extended"], default="stable")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    asyncio.run(main(args.profile, args.timeout))
