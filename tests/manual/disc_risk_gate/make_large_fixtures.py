"""Generate the large fixtures for the DISC Risk Gate's length and paging tests.

Run from anywhere:  python tests/manual/disc_risk_gate/make_large_fixtures.py

All data is synthetic. Sizes assume the default classifier_max_input_tokens
(16384) and Clef's ~2.3 characters per token on CSV-like data.
"""

import random
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
ITEMS = ["pipette tips", "nitrile gloves", "falcon tubes", "lab notebooks",
         "ethanol 70%", "kimwipes", "petri dishes", "cryo boxes", "parafilm"]
ROOMS = ["Steele 101", "Burke 220", "Life Sciences 314", "Vail 502", "Remsen 112"]


def inventory_rows(n: int, rng: random.Random) -> list[str]:
    return [
        f"{i},{rng.choice(ITEMS)},{rng.randint(1, 500)},{rng.choice(ROOMS)},"
        f"2026-{rng.randint(1, 10):02d}-{rng.randint(1, 28):02d}"
        for i in range(1, n + 1)
    ]


def write(name: str, text: str) -> None:
    (FIXTURES / name).write_text(text)
    print(f"{name}: {len(text):,} characters")


def main() -> None:
    rng = random.Random(14)
    header = "row,item,quantity,room,last_ordered"

    # ~45k chars: view_attachment returns 10k chars per page, so the SSN in the
    # last row only reaches the model (and the gate) once the model pages to it.
    rows = inventory_rows(1000, rng)
    rows.append("1001,NOTE: reimburse Jordan Avery SSN 078-05-1120 DOB 1990-03-14,0,Steele 101,2026-10-28")
    write("long_inventory_ssn_at_end.csv", "\n".join([header, *rows]) + "\n")

    # ~25k chars (~8-10k tokens): fits within the classifier's input. Should pass.
    write("under_limit_paste.txt", "\n".join([header, *inventory_rows(560, rng)]) + "\n")

    # ~70k chars (~30k tokens): under the 8x pre-check (131,072 chars), so it is
    # sent to Clef, which reports input_tokens == 16384 -> request blocked.
    write("too_long_paste.txt", "\n".join([header, *inventory_rows(1550, rng)]) + "\n")

    # ~140k chars: over the pre-check, blocked without calling the classifier.
    write("way_too_long_paste.txt", "\n".join([header, *inventory_rows(3100, rng)]) + "\n")


if __name__ == "__main__":
    main()
