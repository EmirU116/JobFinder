"""Review the applications the agents prepared, and track their status.

  python review.py                         # step through jobs that are ready_for_review
  python review.py --list                  # show every job and its status
  python review.py --mark <job_id> applied # update a status after you've applied
"""

import argparse
import sys
import webbrowser

from jobfinder import store


def show(row: dict) -> None:
    print("=" * 70)
    print(f"{row['job_id']}  [{row['status']}]")
    print(f"{row['role']} @ {row['company']}")
    print(f"{row['location']} | {row['work_mode']} | lang: {row['language']} | deadline: {row['deadline'] or '-'}")
    print(f"Ad:    {row['url']}")
    print(f"Apply: {row['apply_method']}")
    if row["notes"]:
        print(f"Notes: {row['notes']}")


def review() -> None:
    pending = [r for r in store.read_rows() if r["status"] == "ready_for_review"]
    if not pending:
        print("Nothing to review.")
        return
    for i, row in enumerate(pending, 1):
        show(row)
        letter = store.letter_file(row)
        print("-" * 70)
        print(letter.read_text(encoding="utf-8") if letter.exists() else f"(letter missing: {letter})")
        print("-" * 70)
        while True:
            choice = input(f"({i}/{len(pending)}) [a]pprove  [s]kip  [o]pen ad  [n]ext  [q]uit: ").strip().lower()
            if choice == "o":
                webbrowser.open(row["url"])
                continue
            if choice == "a":
                store.set_status(row["job_id"], "approved")
                print(f"Approved. Letter: {letter}")
            elif choice == "s":
                store.set_status(row["job_id"], "skipped")
            elif choice == "q":
                return
            break


def list_all() -> None:
    rows = store.read_rows()
    if not rows:
        print("No jobs tracked yet.")
    for r in rows:
        print(f"{r['status']:<17} {r['job_id']:<30} {r['company'][:25]:<25} {r['role'][:35]:<35} {r['work_mode']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--mark", nargs=2, metavar=("JOB_ID", "STATUS"), help=f"STATUS: {', '.join(store.STATUSES)}")
    args = parser.parse_args()

    if args.mark:
        try:
            row = store.set_status(*args.mark)
        except (KeyError, ValueError) as e:
            sys.exit(str(e))
        print(f"{row['job_id']} -> {row['status']}")
    elif args.list:
        list_all()
    else:
        review()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
