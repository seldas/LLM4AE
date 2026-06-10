import sqlite3
import json
import argparse
import sys
import os
import time
import warnings
from pathlib import Path
from multiprocessing import get_context, current_process, set_start_method

# Add project root / import paths
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root / "server"))
sys.path.append(str(project_root / "development" / "NER" / "scripts"))

import custom_scorer  # registers ade_weighted_ner_scorer.v1

DB_PATH = project_root / "server" / "database" / "llm4ae.db"


def fetch_cases(force=False, limit=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE migration_key = 'BERT'")
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        raise RuntimeError("BioBERT user (migration_key='BERT') not found in database.")

    bert_user_id = user_row["id"]

    cursor.execute("SELECT id, pages, meta FROM cases")
    raw_cases = cursor.fetchall()
    conn.close()

    cases = []
    skipped_count = 0

    for case in raw_cases:
        case_id = case["id"]
        meta = json.loads(case["meta"]) if case["meta"] else {}

        if not force and meta.get("bert_processed") == "Done":
            skipped_count += 1
            continue

        pages = json.loads(case["pages"]) if case["pages"] else [""]
        narrative = pages[0] if pages else ""

        if not narrative or not narrative.strip():
            continue

        cases.append({
            "case_id": case_id,
            "narrative": narrative,
            "meta": meta,
        })

    if limit is not None:
        cases = cases[:limit]

    return bert_user_id, cases, skipped_count


def chunk_list(items, n_chunks):
    chunks = [[] for _ in range(n_chunks)]
    for i, item in enumerate(items):
        chunks[i % n_chunks].append(item)
    return chunks


def _suppress_noisy_warnings():
    # Suppress repeated PyTorch CUDA capability warning spam in each worker.
    warnings.filterwarnings(
        "ignore",
        message=r"Found GPU0 .* compute capability .*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r"The following list shows the CCs .*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r"Please follow the instructions at https://pytorch\.org/get-started/locally/.*",
        category=UserWarning,
    )


def gpu_worker(gpu_id, case_batch, result_queue):
    """
    One worker process per GPU.
    Loads the model once, runs inference for its assigned cases,
    and sends results back to the parent process.
    """
    try:
        # Restrict this process to one GPU before importing GPU libraries
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

        _suppress_noisy_warnings()

        import spacy
        spacy.require_gpu(0)

        from ner_client import get_ner_client
        client = get_ner_client()

        # Notify parent that this worker is ready
        result_queue.put({
            "type": "worker_started",
            "gpu_id": gpu_id,
            "total_cases": len(case_batch),
        })

        for item in case_batch:
            case_id = item["case_id"]
            narrative = item["narrative"]
            meta = item["meta"]

            try:
                entities = client.annotate_text(narrative)
                result_queue.put({
                    "type": "case_result",
                    "ok": True,
                    "gpu_id": gpu_id,
                    "case_id": case_id,
                    "entities": entities,
                    "meta": meta,
                    "error": None,
                })
            except Exception as e:
                result_queue.put({
                    "type": "case_result",
                    "ok": False,
                    "gpu_id": gpu_id,
                    "case_id": case_id,
                    "entities": None,
                    "meta": meta,
                    "error": str(e),
                })

    except Exception as e:
        result_queue.put({
            "type": "worker_init_error",
            "gpu_id": gpu_id,
            "case_id": None,
            "entities": None,
            "meta": None,
            "error": f"Worker on GPU {gpu_id} failed to initialize: {e}",
        })

    finally:
        result_queue.put({
            "type": "worker_done",
            "gpu_id": gpu_id,
        })


def write_result(conn, bert_user_id, result):
    case_id = result["case_id"]
    entities = result["entities"]
    meta = result["meta"]

    conn.execute("BEGIN")
    try:
        conn.execute(
            "DELETE FROM annotations WHERE case_id = ? AND user_id = ?",
            (case_id, bert_user_id),
        )

        for ent in entities:
            conn.execute(
                """
                INSERT INTO annotations
                (case_id, user_id, label, start_offset, end_offset, text_content, note, relationships, adjudication)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    bert_user_id,
                    ent["label"],
                    ent["start"],
                    ent["end"],
                    ent["text"],
                    "BERT",
                    "{}",
                    None,
                ),
            )

        meta["bert_processed"] = "Done"
        conn.execute(
            "UPDATE cases SET meta = ? WHERE id = ?",
            (json.dumps(meta), case_id),
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise


def format_progress_bar(done, total, width=24):
    if total <= 0:
        return "[" + ("." * width) + "]"
    filled = int(width * done / total)
    if filled > width:
        filled = width
    return "[" + ("#" * filled) + ("." * (width - filled)) + "]"


def render_progress(gpu_progress, processed_count, total_cases, skipped_count, error_count, done_workers, num_workers, started_at):
    elapsed = max(time.time() - started_at, 1e-6)
    rate = processed_count / elapsed
    overall_bar = format_progress_bar(processed_count, total_cases, width=32)

    lines = []
    lines.append(
        f"Overall {overall_bar} {processed_count}/{total_cases} | "
        f"Skipped: {skipped_count} | Errors: {error_count} | "
        f"Workers done: {done_workers}/{num_workers} | "
        f"{rate:.2f} cases/s"
    )

    for gpu_id in sorted(gpu_progress):
        info = gpu_progress[gpu_id]
        done = info["done"]
        total = info["total"]
        status = info["status"]
        bar = format_progress_bar(done, total, width=20)
        lines.append(f"GPU {gpu_id:<2} {bar} {done:>4}/{total:<4} {status}")

    return lines


def print_progress(lines, prev_line_count):
    # Move cursor up to redraw previous block
    if prev_line_count > 0:
        sys.stdout.write(f"\x1b[{prev_line_count}A")

    for line in lines:
        sys.stdout.write("\x1b[2K")  # clear line
        sys.stdout.write(line + "\n")

    sys.stdout.flush()
    return len(lines)


def batch_annotate_multi_gpu(force=False, limit=None, num_gpus=8):
    bert_user_id, cases, skipped_count = fetch_cases(force=force, limit=limit)

    print(f"BioBERT User ID: {bert_user_id}")
    print(f"Cases to process: {len(cases)}")
    print(f"Skipped already processed: {skipped_count}")

    if not cases:
        print("No cases to process.")
        return

    num_workers = min(num_gpus, len(cases))
    case_chunks = chunk_list(cases, num_workers)

    ctx = get_context("spawn")
    result_queue = ctx.Queue(maxsize=100)

    workers = []
    gpu_progress = {}

    for gpu_id in range(num_workers):
        gpu_progress[gpu_id] = {
            "done": 0,
            "total": len(case_chunks[gpu_id]),
            "status": "starting",
        }

    for gpu_id in range(num_workers):
        p = ctx.Process(
            target=gpu_worker,
            args=(gpu_id, case_chunks[gpu_id], result_queue),
            name=f"gpu-worker-{gpu_id}",
        )
        p.start()
        workers.append(p)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    processed_count = 0
    error_count = 0
    done_workers = 0
    started_at = time.time()
    prev_line_count = 0

    # Initial empty progress render
    lines = render_progress(
        gpu_progress=gpu_progress,
        processed_count=processed_count,
        total_cases=len(cases),
        skipped_count=skipped_count,
        error_count=error_count,
        done_workers=done_workers,
        num_workers=num_workers,
        started_at=started_at,
    )
    prev_line_count = print_progress(lines, prev_line_count)

    while done_workers < num_workers:
        result = result_queue.get()
        msg_type = result.get("type")

        if msg_type == "worker_started":
            gpu_id = result["gpu_id"]
            gpu_progress[gpu_id]["status"] = "running"

        elif msg_type == "worker_init_error":
            gpu_id = result["gpu_id"]
            gpu_progress[gpu_id]["status"] = "init failed"
            error_count += 1

            # Print error below progress block, then redraw block
            sys.stdout.write("\x1b[2K")
            sys.stdout.write(result["error"] + "\n")
            sys.stdout.flush()

        elif msg_type == "worker_done":
            gpu_id = result["gpu_id"]
            done_workers += 1
            if gpu_progress[gpu_id]["status"] not in {"init failed"}:
                gpu_progress[gpu_id]["status"] = "done"

        elif msg_type == "case_result":
            gpu_id = result["gpu_id"]
            case_id = result["case_id"]

            if result["ok"]:
                try:
                    write_result(conn, bert_user_id, result)
                    processed_count += 1
                    gpu_progress[gpu_id]["done"] += 1
                    if gpu_progress[gpu_id]["done"] < gpu_progress[gpu_id]["total"]:
                        gpu_progress[gpu_id]["status"] = "running"
                except Exception as e:
                    error_count += 1
                    gpu_progress[gpu_id]["done"] += 1
                    sys.stdout.write("\x1b[2K")
                    sys.stdout.write(f"DB write failed for case {case_id}: {e}\n")
                    sys.stdout.flush()
            else:
                error_count += 1
                gpu_progress[gpu_id]["done"] += 1
                sys.stdout.write("\x1b[2K")
                sys.stdout.write(f"Error processing case {case_id}: {result['error']}\n")
                sys.stdout.flush()

            if gpu_progress[gpu_id]["done"] >= gpu_progress[gpu_id]["total"] and gpu_progress[gpu_id]["status"] != "init failed":
                gpu_progress[gpu_id]["status"] = "finishing"

        lines = render_progress(
            gpu_progress=gpu_progress,
            processed_count=processed_count,
            total_cases=len(cases),
            skipped_count=skipped_count,
            error_count=error_count,
            done_workers=done_workers,
            num_workers=num_workers,
            started_at=started_at,
        )
        prev_line_count = print_progress(lines, prev_line_count)

    for p in workers:
        p.join()

    conn.close()

    print("\nBatch processing complete.")
    print(f"Processed: {processed_count}")
    print(f"Skipped:   {skipped_count}")
    print(f"Errors:    {error_count}")


if __name__ == "__main__":
    set_start_method("spawn", force=True)

    parser = argparse.ArgumentParser(
        description="Batch annotate ICSR narratives using BioBERT on multiple GPUs."
    )
    parser.add_argument("--force", action="store_true", help="Re-annotate cases even if already processed.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of processed records.")
    parser.add_argument("--num-gpus", type=int, default=8, help="Number of GPUs / worker processes to use.")
    args = parser.parse_args()

    batch_annotate_multi_gpu(force=args.force, limit=args.limit, num_gpus=args.num_gpus)